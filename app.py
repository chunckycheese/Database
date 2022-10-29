from flask import Flask, render_template, request
from flask import redirect, session, url_for, escape, flash, jsonify
import pymysql
import os
import uuid
import random
import shortuuid
from passlib.hash import pbkdf2_sha256
from datetime import date
app = Flask(__name__)

# Make the WSGI interface available at the top level so wfastcgi can get it.
wsgi_app = app.wsgi_app

ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg", "gif"])

# image folder path
imagepath = os.path.dirname(__file__)


# Create connection to the database
def create_connection():
    return pymysql.connect(
        host="10.0.0.17",
        user="penzhang",
        password="ARSIS",
        db="penzhang_students",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor)


# Create session ID
def resource_owner(userid):
    if "user_id" in session:
        connection = create_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE (userID=%s)"
            cursor.execute(sql, int(userid))
            user = cursor.fetchone()
            cursor.close()
            if not bool(user):
                return False
            return user["userID"] == session["user_id"] if True else False
    else:
        print("False")
        return False

# if no email is inputted, return false, else true
def email_is_unique(email):
    if email:
        connection = create_connection()
        with connection.cursor() as cursor:
            sql = "SELECT email FROM users WHERE (email=%s)"
            cursor.execute(sql, email)
            user = cursor.fetchone()
            cursor.close()
            if not bool(user):
                return True
            else:
                return False
    else:
        return False


# Checks if E-mail already exists, or if field was left empty
@app.route('/email_checker', methods=['POST'])
def email_check():
    connection = None
    cursor = None
    try:
        email = request.form['email']
        # validate the received values
        if email and request.method == 'POST':
            connection = create_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email=%s", email)
                row = cursor.fetchone()
                # if no email is inputted, display error
                if row:
                        resp = jsonify({"""'response':
                                        '<span style=\'color:red;\'>
                                        Email unavailable</span>'"""})
                        resp.status_code = 404
                        return resp
                else:
                # if email is valid
                        resp = jsonify({"""'response':
                                       '<span style=\'color:green;\'>
                                       Email available</span>'"""})
                        resp.status_code = 200
                        return resp
        else:
        # if no email is inputted, display error
                resp = jsonify({"""'response':
                              '<span style=\'color:red;\'>
                              Email is required field.</span>'"""})
                resp.status_code = 400
                return resp
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        connection.close()


PUBLIC_PAGES = set(["index",
                    "login", "register", "static"])  # global whitelisting


# checks if user is logged in, else redirects back to login page
@app.before_request
def before_request():
    if "logged_in" not in session and request.endpoint not in PUBLIC_PAGES:
        return redirect(url_for("login"))


# opening a index page
@app.route('/', methods=["get", "post"])
def index():
    """Renders a sample page."""
    return render_template("index.html")


# User registration
@app.route('/register', methods=['get', 'post'])
def register():
    connection = create_connection()
    if request.method == "POST":
        get = request.form
        # Gathers user information from form
        first_name = get["firstName"]
        last_name = get["lastName"]
        email = get["email"]
        pass_word = get["password"]
        roleID = 1
        hashpass = pbkdf2_sha256.hash(pass_word)
        pass_word = hashpass
        if(email_is_unique(request.form["email"])) is False:
            flash("Email Taken")
            return redirect("/register")
        connection = create_connection()
        with connection.cursor() as cursor:
            sql = """INSERT INTO `Users` (firstName, lastName, email, password, roleID)
            VALUES (%s,%s,%s,%s,%s)"""  # Inserting data into db
            val = (first_name, last_name, email, pass_word, roleID)
            cursor.execute(sql, val)
            connection.commit()
        cursor.close
        return redirect("/dashboard")
    return render_template("register.html")


# log user into dashboard
@app.route('/login', methods=['GET', 'POST'])
def login():
    url = request.args.get('ReturnUrl')
    if request.method == "POST":
        user_email = request.form["email"]
        password = request.form["password"]
        connection = create_connection()
        with connection.cursor() as cursor:
            login_sql = "SELECT * FROM users WHERE email = %s"
            val = (user_email)
            cursor.execute(login_sql, val)
            user_data = cursor.fetchone()
        connection.close()
        if bool(user_data) is False:  # login failed
            return render_template('login.html')

        else:
            passhash = pbkdf2_sha256.verify(password, user_data['password'])
            # Hash password
            if passhash:
                f = user_data["userID"]
                # Setup session user&roleID
                session["userID"] = user_data["userID"]
                session["roleID"] = user_data["roleID"]
                session["logged_in"] = True
                return redirect("/dashboard")
            else:
                # Display error message
                return render_template('login.html', error="Wrong credentials")
    return render_template('login.html')


# log user out of dashboard page
@app.route("/logout", methods=["GET", "POST"])
def sign_out():
    try:
        session.pop("logged_in", None)
        session.pop("user_id", None)
        session.pop("roleID", None)
    except:
        True
    finally:
        return redirect(url_for("index"))


# Displays all user information
@app.route('/dashboard')
def dashboard():
    user_id = session["userID"]
    role_id = session["roleID"]
    connection = create_connection()
    with connection.cursor() as cursor:
        # connect roles to users table
        sql = """SELECT
    *
FROM
    roles
    INNER JOIN
    users
    ON
        roles.roleID = users.roleID"""
        if(role_id == 1):
            sql = sql+" WHERE users.userID="+str(user_id)
        cursor.execute(sql)
        users = cursor.fetchall()
        role_sql = """ SELECT * FROM Roles """
        cursor.execute(role_sql)
        roles = cursor.fetchall()

        # displays all information from subject page
        subject_sql = """ SELECT * FROM subjects """
        cursor.execute(subject_sql)
        subjects = cursor.fetchall()
    connection.close
    return render_template('/dashboard.html', users=users,
                           roles=roles, subjects=subjects)


# edit user information from database
@app.route("/edit_user", methods=["GET", "POST"])
def edit_user():
    user_id = request.args.get('id')  # get the id parameter value
    connection = create_connection()
    if request.method == "POST":
        first_name = request.form["fname"]
        last_name = request.form["lname"]
        email = request.form["email"]
        userid = request.form["userid"]
        password = request.form["password"]
        if password != '':
            # generate new salt, and hash a password
            pass_hashed = pbkdf2_sha256.hash(request.form["password"])
            values = (email, first_name, last_name, pass_hashed, userid)
        else:
            values = (email, first_name, last_name, userid)
        with connection.cursor() as cursor:

                if password != '':
                    # Update record
                    update_sql = """UPDATE users SET users.email=%s,
                    users.firstName = %s,users.lastName=%s,
                    users.password=%s  WHERE users.userID = %s"""
                else:
                    update_sql = """UPDATE users SET users.email=%s,
                    users.firstName = %s,users.lastName=%s
                    WHERE users.userID = %s"""  # Update record
                cursor.execute(update_sql, (values))
                connection.commit()  # save or commit values in dbase
                cursor.close()
                return redirect("/dashboard")
    # check if user owns record
    # no match and user is not admin
    if not resource_owner(user_id) and session['roleID'] == 1:
        return redirect("/dashboard")
    with connection.cursor() as cursor:
        sql = "SELECT * FROM users WHERE userID = %s"
        val = (int(user_id))
        cursor.execute(sql, val)
        user_info = cursor.fetchone()
        sql_role = "SELECT * FROM roles"
        cursor.execute(sql_role)
        role_info = cursor.fetchall()
        return render_template("edit_user.html", user=user_info,
                               roles=role_info, title="Editing User")


# removing subject from database
@app.route("/remove_subject", methods=["GET"])
def remove_subject():
    subject_id = request.args.get("id")  # get id parameter value
    connection = create_connection()
    with connection.cursor() as cursor:
        # delete record
            delete_subject_sql = "DELETE FROM subjects WHERE subjectID=%s"
            value = (int(subject_id))
            cursor.execute(delete_subject_sql, value)
            # save dbase
            connection.commit()
            # close cursor
            cursor.close()
    return redirect("/dashboard")


# delete the user from the db
@app.route("/delete_user", methods=["GET"])
def deleteuser():
    user_id = request.args.get("id")  # get id parameter value
    connection = create_connection()
    with connection.cursor() as cursor:
        # delete record
            delete_sql = "DELETE FROM users WHERE userID=%s"
            value = (int(user_id))
            cursor.execute(delete_sql, value)
            # save dbase
            connection.commit()
            # close cursor
            cursor.close()
    return redirect("/dashboard")


# if on admin page, check if user is admin, else return to dashboard
@app.route("/view_role")
def role():
    roleid = request.args.get("id")  # get id value
    if not resource_owner(roleid):
        return redirect("/dashboard")
    connection = create_connection()
    with connection.cursor() as cursor:
        sql = "SELECT * From roles WHERE roleID=%s"
        values = (roleid)
        cursor.execute(role_sql, values)
        # fetch user with specified id
        user_info = cursor.fetchone()
    connection.close()
    print(resource_owner(userid))
    return render_template("user.html", user=user_info)


# add new subject for user 
@app.route('/add_subject', methods=["GET", "POST"])
def add_subject():
    connection = create_connection()
    userID = request.args.get('id')
    userid = session['userID']  # if user
    with connection.cursor() as cursor:
        # select all subjectid
        selected_sql = "SELECT subjectID FROM usersubjects WHERE userID = %s"
        val = session['userID']
        cursor.execute(selected_sql, val)

        selected_subject = cursor.fetchall()

        # find all subjectid
        selected_subject_list = [i["subjectID"] for i in selected_subject]
        print(len(selected_subject_list))
            
        if request.method == "POST":
            userID = request.form["userID"]
            subject_id_list = request.form.getlist('subjects')

            for  subjectid in subject_id_list:
                subjectid = int(subjectid)  # convert from str to int 
                # If subject already selected, remove from list
                if subjectid in selected_subject_list: 
                    flash("You cannot select the same subject twice!")
                    selected_subject_list.remove(subjectid)
                    # return redirect("/dashboard")
                # Not already selected, check if we are adding less than 5
                elif (len(selected_subject_list)) < 5:
                    sql_add = """INSERT INTO usersubjects
                    (userID,subjectID) values (%s,%s)"""
                    val = (userID, subjectid)
                    cursor.execute(sql_add, val)
                    connection.commit()
                    selected_subject_list.append(1)
                    print(selected_subject_list)
                else:
                    flash("You cannot select more than 5 subjects!")
            return redirect("/dashboard")
            
        # fetch subject to display
        today = date.today()
        subject_sql = """SELECT * FROM subjects WHERE
        subjectStartDate <= %s AND %s <= subjectEndDate"""
        cursor.execute(subject_sql, (today, today))
        subject_info = cursor.fetchall()
        return render_template("add_subject.html", subjects=subject_info,
                               userID=userID,
                               selected_subject=selected_subject)


# edit the information of the subject
@app.route("/edit_subject", methods=["GET", "POST"])
def editsubject():
    subject_id = request.args.get('id')  # get the id parameter value
    connection = create_connection()
    with connection.cursor() as cursor:
        if request.method == "POST":
            subject_id = request.form["subject_id"]
            subject_name = request.form["subjectName"]
            start_date = request.form["subjectStartDate"]
            end_date = request.form["subjectEndDate"]
            update_sql = """UPDATE subjects SET subjectName=%s, subjectStartDate = %s,
                        subjectEndDate=%s
                        WHERE subjectID = %s"""  # Update record
            values = (subject_name, start_date, end_date, subject_id)
            cursor.execute(update_sql, (values))
            connection.commit()  # save or commit values in dbase
            cursor.close()
            return redirect("/dashboard")

        sql = "SELECT * FROM subjects WHERE subjectID = %s"
        val = (int(subject_id))
        cursor.execute(sql, val)
        subject_info = cursor.fetchone()
        return render_template("edit_subject.html", subject=subject_info)


# deleting the subjects that students have selected
@app.route("/delete_subject", methods=["GET"])
def delete_subject():
    user_id = request.args.get("id")  # get id parameter value
    subject_id = request.args.get("subjectid")
    connection = create_connection()
    with connection.cursor() as cursor:
        # delete record
            delete_sql = """DELETE FROM usersubjects WHERE
            (UserID = %s and subjectID = %s)"""
            value = (int(user_id), subject_id)
            cursor.execute(delete_sql, value)
            # save dbase
            connection.commit()
            # close cursor
            cursor.close()
    return redirect("/dashboard")


# view the subjects that users are taking 
@app.route('/view_subject', methods=["get", "post"])
def view_subject():
    user_id = request.args.get('id')  # get the id parameter value
    role_id = session["roleID"]
    connection = create_connection()
    with connection.cursor() as cursor:
        # connect usersubjects to users table
        sql = """SELECT
    *,
    usersubjects.subjectID,
    usersubjects.userID,
    subjects.subjectName,
    users.firstName,
    users.lastName
FROM
    subjects
    INNER JOIN
    usersubjects
    ON
        subjects.subjectID = usersubjects.subjectID
    INNER JOIN
    users
    ON
        users.userID = usersubjects.userID WHERE users.userID = %s
        """
        cursor.execute(sql, int(user_id))
        users = cursor.fetchall()
        role_sql = """ SELECT * FROM Roles """
        cursor.execute(role_sql)
        roles = cursor.fetchall()
    connection.close
    return render_template('/view_subject.html', users=users, roles=roles)


# allow admins to create new subjects in databases
@app.route("/create_subject", methods=["GET", "POST"])
def create_subject():
    connection = create_connection()
    if request.method == "POST":
        get = request.form
        # retrieve information from the form and put it in a new variable 
        subjectname = get["subjectName"]
        subjectstartdate = get["startDate"]
        subjectenddate = get["endDate"]
        connection = create_connection()
        with connection.cursor() as cursor:
            # insert the information into the db
            sql = """INSERT INTO subjects (subjectName, subjectStartDate, subjectEndDate) 
            VALUES (%s, %s, %s)"""
            val = (subjectname, subjectstartdate, subjectenddate)
            cursor.execute(sql, val)
            connection.commit()
        cursor.close
        return redirect("/dashboard")
    return render_template("create_subject.html")


# view all students that are taking one specific subject
@app.route('/view_students', methods=["get", "post"])
def view_students():
    subject_id = request.args.get('id')  # get the id parameter value
    role_id = session["roleID"]
    connection = create_connection()
    with connection.cursor() as cursor:
        # connect usersubjects to users table
        sql = """SELECT
        subjects.subjectID,
        users.firstName,
        users.lastName,
        subjects.subjectName,
        usersubjects.subjectID,
        usersubjects.userID,
        users.userID
        FROM
        subjects
        INNER JOIN
        usersubjects
        ON
            subjects.subjectID = usersubjects.subjectID
        INNER JOIN
        users
        ON
            usersubjects.userID = users.userID WHERE subjects.subjectID = %s
            """
        cursor.execute(sql, int(subject_id))
        users = cursor.fetchall()
        connection.close
        return render_template('/view_students.html', users=users)

# Don't leave anything below this
if __name__ == '__main__':
    app.secret_key = "os.urandom(69)"
    import os
    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT, debug=True)
