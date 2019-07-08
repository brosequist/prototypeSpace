import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    userid=session["user_id"]
    # Get all records from stock inventory for the user
    getstocklist = db.execute("SELECT symbol, companyname, numbershares FROM stockinventory WHERE userid=:userid", userid=userid)
    
    # Add current share price and total value to each record, sum prices across stocks
    totalstockvalue = float(0.00)
    for record in getstocklist:
        quote=lookup(record['symbol'])
        record['shareprice'] = usd(float(quote['price']))
        record['totalvalue'] = usd(float(quote['price']*record['numbershares']))
        totalstockvalue=totalstockvalue+float(quote['price']*record['numbershares'])
    
    # Get current user cash balance
    usermoneylist=db.execute("SELECT cash FROM users WHERE id = :userid", userid=userid)
    usermoneycount = float("0.00")
    for item in usermoneylist:
        usermoneycount = usermoneycount + float(item.get("cash",""))
    
    totalvalue = usermoneycount+totalstockvalue
    
    return render_template("index.html", stocktable=getstocklist, totalstockvalue=usd(totalstockvalue), cashbalance=usd(usermoneycount), totalvalue=usd(totalvalue))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        
        # Ensure stock symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide ticker symbol")

        # Ensure shares are greater than zero and not fractional
        
        if not request.form.get("shares").isdigit():
            return apology("invalid number of shares")
        
        sharestobuy = int(request.form.get("shares"))
        if sharestobuy < 1:
            return apology("invalid number of shares")

        # Get stock information and validate if symbol exists
        quote=lookup(request.form.get("symbol"))
        if not quote:
            return apology("symbol does not exist")

        # Get the amount of money user has, and provide error if not enough
        userid=session["user_id"]
        usermoneylist=db.execute("SELECT cash FROM users WHERE id = :userid", userid=userid)

        usermoneycount = float("0.00")
        for item in usermoneylist:
            usermoneycount = usermoneycount + float(item.get("cash",""))
        
        usermoney=usermoneycount
        shareprice=float(quote['price'])
        totalamount=(shareprice * sharestobuy)
        
        if usermoney < totalamount:
            return apology("Not enough money for purchase")

        # Store other company info
        companyname=quote['name']
        companysymbol=quote['symbol']

        # Update transaction history
        insertrow = db.execute("INSERT INTO transactionhistory ('transactionshares', 'symbol', 'transactionamount', 'transactiontype', 'userid') VALUES (:transactionshares, :symbol, :transactionamount, 'BUY', :userid)", transactionshares=sharestobuy, symbol=companysymbol, transactionamount=round(totalamount, 2), userid=userid)

        if not insertrow:
            return apology("unable to insert transaction history")

        # Update stock inventory
        insertrow = db.execute("INSERT INTO stockinventory ('symbol', 'companyname', 'numbershares', 'userid') VALUES (:symbol, :companyname, :transactionshares, :userid)", symbol=companysymbol, companyname=companyname, transactionshares=sharestobuy, userid=userid)

        if not insertrow:
            return apology("unable to add to stock inventory")

        # Update user cash
        usermoney = usermoney - totalamount
        updaterow = db.execute("UPDATE users SET cash = ':usermoney' WHERE id = :userid", usermoney=round(usermoney, 2), userid=userid)

        if not updaterow:
            return apology("unable to update user cash balance")

        return render_template("bought.html", quote=quote, totalamount=usd(totalamount), usermoney=usd(usermoney), shares=sharestobuy)
        
    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check(username):
    """Return true if username available, else false, in JSON format"""
    
    # Query database for username
    rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)
                      
    # Ensure username exists and password is correct
    if len(rows) != 1:
        return jsonify(True)
    
    return jsonify(False)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    
    userid=session["user_id"]
    historylist=db.execute("SELECT transactiontype, symbol, transactionamount, transactionshares, transactiondatetime FROM transactionhistory WHERE userid=:userid", userid=userid)
    if not historylist:
        return apology("can not retreive history")
    
    for record in historylist:
        record['transactionamount'] = usd(record['transactionamount'])
    
    return render_template("history.html", historylist=historylist)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("symbol"):
            return apology("must provide ticker symbol")
        
        quote=lookup(request.form.get("symbol"))
        if not quote:
            return apology("symbol does not exist")
                
        usdPrice=usd(quote['price'])
        
        return render_template("quoted.html", quote=quote, usdPrice=usdPrice)
    
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")

    
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    
     # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")
        
        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
        
        # Ensure password was confirmed
        elif not request.form.get("confirmation"):
            return apology("must confirm password")
        
        # Ensure that password and confirmation password match
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("password and confirmation do not match")
                
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Ensure that username does not exist
        if rows:
            return apology("username already exists")
    
        # Insert username and password to finance.db; password hashed using generate_password_hash
        insertrow = db.execute("INSERT INTO users ('username', 'hash') VALUES (:username, :passhash)", username=request.form.get("username"), passhash=generate_password_hash(request.form.get("password")))
        
        if not insertrow:
            return apology("Error creating user")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

    
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
             
        # Ensure stock symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide ticker symbol")

        # Ensure shares are greater than zero and not fractional
        if not request.form.get("shares").isdigit():
            return apology("invalid number of shares")
        
        sharestosell = int(request.form.get("shares"))
        if sharestosell < 1:
            return apology("invalid number of shares")

        # Get stock information and validate if symbol exists
        quote=lookup(request.form.get("symbol"))
        if not quote:
            return apology("symbol does not exist")
        
        # Validate if user has stock
        userid=session["user_id"]
        getstockcount=db.execute("SELECT numbershares FROM stockinventory WHERE userid = :userid AND symbol = :symbol", userid=userid, symbol=request.form.get("symbol"))
        if not getstockcount:
            return apology("no shares owned")
        
        # Get stock count
        numberofshares = int(0)
        for item in getstockcount:
            numberofshares = numberofshares + int(item.get("numbershares", ""))
        
        # Validate if shares requested is less than or equal to number of shares held
        if sharestosell > numberofshares:
            return apology("sell request exceeds number of shares owned")
        
        # Get the amount of money user has, and provide error if not enough
        usermoneylist=db.execute("SELECT cash FROM users WHERE id = :userid", userid=userid)
        usermoneycount = float("0.00")
        for item in usermoneylist:
            usermoneycount = usermoneycount + float(item.get("cash",""))
        
        usermoney=usermoneycount
        shareprice=float(quote['price'])
        totalamount=(shareprice * sharestosell)
        
        # Store other company info
        companyname=quote['name']
        companysymbol=quote['symbol']

        # Update transaction history
        insertrow = db.execute("INSERT INTO transactionhistory ('transactionshares', 'symbol', 'transactionamount', 'transactiontype', 'userid') VALUES (:transactionshares, :symbol, :transactionamount, 'SELL', :userid)", transactionshares=sharestosell, symbol=companysymbol, transactionamount=round(totalamount, 2), userid=userid)

        if not insertrow:
            return apology("unable to insert transaction history")

        # Update stock inventory
        # Delete inventory record if zero shares exist after trade
        if sharestosell == numberofshares:
            deleterow = db.execute("DELETE FROM stockinventory WHERE userid = :userid AND symbol = :symbol", userid=userid, symbol=companysymbol)

            if not deleterow:
                return apology("unable to liquidate stock inventory")
            
        # Otherwise, update share count
        else:
            updaterow = db.execute("UPDATE stockinventory SET numbershares = :sharedifference WHERE userid = :userid AND symbol = :symbol", sharedifference = (numberofshares - sharestosell), userid=userid, symbol=companysymbol)

            if not updaterow:
                return apology("unable to update stock inventory")

        # Update user cash
        usermoney = usermoney + totalamount
        updaterow = db.execute("UPDATE users SET cash = ':usermoney' WHERE id = :userid", usermoney=round(usermoney,2), userid=userid)

        if not updaterow:
            return apology("unable to update user cash balance")

        return render_template("sold.html", quote=quote, totalamount=usd(totalamount), usermoney=usd(usermoney), shares=sharestosell)
        
    else:
        userid=session["user_id"]
        selloptions=db.execute("SELECT symbol FROM stockinventory WHERE userid = :userid", userid=userid)
        
        return render_template("sell.html", selloptions=selloptions)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
