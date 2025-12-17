
from flask import Flask, render_template, request, redirect, session, flash, jsonify
from supabase import create_client
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import os

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = "hackathon_secret_key"   # REQUIRED for session & flash

SUPABASE_URL = "https://ofyhamnfkpgtnujmqgiv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9meWhhbW5ma3BndG51am1xZ2l2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTM4MzIyMiwiZXhwIjoyMDgwOTU5MjIyfQ.YLtXejHgDlLr1es0suj06eP1-WUp7kBriaLgSVf37Ds"  # ⚠️ DO NOT push to GitHub
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- API ROUTES (DROPDOWNS) ----------------

@app.route("/api/districts")
def get_districts():
    data = supabase.table("districts").select("id,name").execute().data
    return jsonify(data)


@app.route("/api/constituencies/<int:district_id>")
def get_constituencies(district_id):
    data = (
        supabase.table("constituencies")
        .select("id,name")
        .eq("district_id", district_id)
        .execute()
        .data
    )
    return jsonify(data)


@app.route("/api/places/<int:constituency_id>")
def get_places(constituency_id):
    data = (
        supabase.table("places")
        .select("id,name")
        .eq("constituency_id", constituency_id)
        .execute()
        .data
    )
    return jsonify(data)

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        phone = request.form.get("phone")
        age = request.form.get("age")
        blood_group = request.form.get("blood_group")
        district = request.form.get("district")
        constituency = request.form.get("constituency")
        place = request.form.get("place")

        # Validation
        if not all([name, email, password, phone, age, blood_group, district, constituency, place]):
            flash("❌ Not registered. Please fill all fields.", "error")
            return redirect("/register")

        # Check existing user
        exists = (
            supabase.table("users")
            .select("id")
            .eq("email", email)
            .execute()
            .data
        )

        if exists:
            flash("❌ Email already registered", "error")
            return redirect("/register")

        try:
            supabase.table("users").insert({
                "id": str(uuid.uuid4()),
                "name": name,
                "email": email,
                "password": generate_password_hash(password),
                "phone": phone,
                "age": int(age),
                "blood_group": blood_group,
                "district_id": int(district),
                "constituency_id": int(constituency),
                "place_id": int(place),
            }).execute()

            flash("✅ Registered successfully. Please login.", "success")
            return redirect("/login")

        except Exception as e:
            print(e)
            flash("❌ Registration failed. Try again.", "error")
            return redirect("/register")

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = (
            supabase.table("users")
            .select("*")
            .eq("email", email)
            .execute()
            .data
        )

        if not user:
            flash("❌ Invalid email or password", "error")
            return redirect("/login")

        user = user[0]

        if not check_password_hash(user["password"], password):
            flash("❌ Invalid email or password", "error")
            return redirect("/login")

        # ✅ store session (UPDATED)
        session["user_id"] = user["id"]
        session["email"] = user["email"]
        session["age"] = user["age"]
        session["blood_group"] = user["blood_group"]
        session["district_id"] = user["district_id"]
        session["constituency_id"] = user["constituency_id"]
        session["place_id"] = user["place_id"]

        return redirect("/dashboard")

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    # Fetch user details
    user_data = (
        supabase.table("users")
        .select("name,email,age,blood_group,district_id,constituency_id,place_id")
        .eq("id", user_id)
        .execute()
        .data
    )

    if not user_data:
        return redirect("/login")

    user = user_data[0]

    # Fetch location names
    district = supabase.table("districts") \
        .select("name") \
        .eq("id", user["district_id"]) \
        .execute().data[0]["name"]

    constituency = supabase.table("constituencies") \
        .select("name") \
        .eq("id", user["constituency_id"]) \
        .execute().data[0]["name"]

    place = supabase.table("places") \
        .select("name") \
        .eq("id", user["place_id"]) \
        .execute().data[0]["name"]

    return render_template(
        "dashboard.html",
        name=user["name"],
        email=user["email"],
        age=user["age"],
        blood_group=user["blood_group"],
        district=district,
        constituency=constituency,
        place=place
    )
@app.route("/alerts")
def user_alerts():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    user = (
        supabase.table("users")
        .select("place_id,blood_group")
        .eq("id", user_id)
        .execute()
        .data
    )[0]

    alerts = (
        supabase.table("blood_requests")
        .select("*")
        .eq("place_id", user["place_id"])
        .eq("blood_group", user["blood_group"])
        .execute()
        .data
    )

    # Fetch user responses
    responses = (
        supabase.table("blood_request_responses")
        .select("blood_request_id,response")
        .eq("user_id", user_id)
        .execute()
        .data
    )

    # Convert to dictionary for easy lookup
    response_map = {
        r["blood_request_id"]: r["response"] for r in responses
    }

    return render_template(
        "user_alerts.html",
        alerts=alerts,
        response_map=response_map
    )


@app.route("/respond/<request_id>", methods=["POST"])
def respond_to_request(request_id):
    if "user_id" not in session:
        return redirect("/login")

    response = request.form.get("response")

    if response not in ["YES", "NO"]:
        return redirect("/alerts")

    data = {
        "id": str(uuid.uuid4()),
        "blood_request_id": request_id,
        "user_id": session["user_id"],
        "response": response
    }

    supabase.table("blood_request_responses").insert(data).execute()

    flash("✅ Response recorded", "success")
    return redirect("/alerts")



# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)
