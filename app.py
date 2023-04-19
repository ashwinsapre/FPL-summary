from flask import Flask, render_template, url_for, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import script

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method=="POST":
        leagueID = request.form['leagueID'] 

        SMTM=553
        FPLPICT=550
        GHS=814181
        RFPL=386899

        _ , _ = script.get_summary_image(leagueID,100)
        return send_file(f'files/{leagueID}summary.png', as_attachment=True)
        #initiate download
    else:
        return render_template("index.html")

if __name__=='__main__':
    app.run(debug=True, port=5001)