from flask import Flask,render_template,request,url_for,redirect,flash,session,abort,send_file
from flask_session import Session
import flask_excel as excel
import mysql.connector
from itsdangerous import URLSafeTimedSerializer
from stoken import token
from key import secret_key,salt,salt2
from otp import genotp
from cmail import sendmail
from io import BytesIO
mydb=mysql.connector.connect(host='localhost',user='root',password='Admin',db='prm')
app=Flask(__name__)
app.config['SESSION_TYPE']='filesystem'
Session(app)
excel.init_excel(app)
app.secret_key=secret_key
@app.route('/')
def welcome():
    return render_template('index.html')
@app.route('/home',methods=['GET','POST'])
def home():
    return render_template('home.html')
@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method=='POST':
        u_id=genotp()
        user=request.form['user']
        email=request.form['email']
        mobile=request.form['mobile']
        address=request.form['address']
        password=request.form['password']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from users where email=%s',[email])
            count=cursor.fetchall()[0]
            print(count)
            if count==1:
                raise Exception
        except Exception as e:
            flash('User already registered')
            return redirect(url_for('index.html'))
        else:
            data={'u_id':u_id,'user':user,'email':email,'mobile':mobile,'address':address,'password':password}
            subject='The link has sent to your email'
            body=f"Click the link to confirm\n{url_for('confirm',token=token(data,salt=salt),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('The link has sent to this mail')
            return redirect(url_for('signup'))
    return render_template('signup.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email,password from users where email=%s and password=%s',[email,password])
        count=cursor.fetchone()
        print(count)
        if count==(email,password):
            session['user']=email
            return redirect(url_for('home'))
    return render_template('login.html')
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt,max_age=300)
    except Exception as e:
        abort(404,'Link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('insert into users(user_id,user_name,email,mobile,address,password) values(%s,%s,%s,%s,%s,%s)',[data['u_id'],data['user'],data['email'],data['mobile'],data['address'],data['password']])
        mydb.commit()
        cursor.close()
        flash('Details registered successfully')
        return redirect(url_for('login'))
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))
@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        print(email)
        npassword=request.form['newpassword']
        cpassword=request.form['confirmpassword']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where email=%s',[email])
        count=cursor.fetchone()[0]
        print(count)
        if count != 1:
            return redirect(url_for('login'))
        elif npassword==cpassword:
            data={'user':email,'password':npassword}
            subject='The reset link for your page login'
            body=f"The reset link for login verify {url_for('verify',token=token(data,salt=salt2),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('The reset password link as sent to given mail')
            return redirect(url_for('forgot'))
    return render_template('forgot.html')
@app.route('/verify/<token>',methods=['GET','POST'])
def verify(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt2,max_age=300)
        print(data['user'])
    except Exception as e:
        abort(404,'link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('update users set password=%s where email=%s',[data['password'],data['email']])
        mydb.commit()
        cursor.close()
        return redirect(url_for('login'))
@app.route('/addnotes',methods=['GET','POST'])
def addnotes():
    if session.get('user'):
        print('hi')
        if request.method=='POST':
            #print('hello')
            title=request.form['title']
            desc=request.form['desc']
            addedby=session.get('user')
            print(addedby)
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into notes(notes_id,title,descr,addedby) values(uuid_to_bin(uuid()),%s,%s,%s)',[title,desc,addedby])      
            mydb.commit()
            cursor.close()
            flash('Your notes has successfully inserted')
            return redirect(url_for('home'))
        return render_template('notes.html')
    else:
        return redirect(url_for('login'))
@app.route('/notes')
def notes():
    if session.get('user'):
        addedby=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(notes_id),title,descr,date from notes where addedby=%s',[addedby])
        count1=cursor.fetchall()
        return render_template('table.html',count1=count1)
    return redirect(url_for('login'))
@app.route('/viewnotes/<nid>',methods=['GET','POST'])
def viewnotes(nid):
    addedby=session.get('user')
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select title,descr from notes where notes_id=uuid_to_bin(%s)',[nid])
    count1=cursor.fetchone()
    print(count1)
    return render_template('viewnotes.html',count1=count1,nid=nid)
@app.route('/update/<nid>',methods=['GET','POST'])
def update(nid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select title,descr from notes where notes_id=uuid_to_bin(%s)',[nid])
        count1=cursor.fetchone()
        cursor.close()
        if request.method=='POST':
            title=request.form['title']
            desc=request.form['desc']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update notes set title=%s,descr=%s where notes_id=uuid_to_bin(%s)',[title,desc,nid])
            mydb.commit()
            cursor.close()
            flash('Your notes details updated successfully')
            return redirect(url_for('notes'))
    return render_template('notes1.html',count1=count1)        
@app.route('/delete/<nid>')
def delete(nid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('delete from notes where notes_id=uuid_to_bin(%s)',[nid])
    mydb.commit()
    cursor.close()
    return redirect(url_for('notes'))
@app.route('/exceldata')
def exceldata():
    if session.get('user'):
        addedby=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select title,descr,date from notes where addedby=%s',[addedby])
        count2=cursor.fetchall()
        cursor.close()
        columns=['Title','Descr','Date']
        array_data=[list(i) for i in count2]
        array_data.insert(0,columns)
        print(array_data)
        response= excel.make_response_from_array(array_data,'xlsx',filenmae='NotesData')
        print(response)
        return response
    else:
        return redirect(url_for('login'))
@app.route('/addfile',methods=['GET','POST'])
def addfile():
    if session.get('user'):
        if request.method=='POST':
            data=request.files.getlist('data')
            addedby=session.get('user')
            cursor=mydb.cursor(buffered=True)
            for file in data:
                file_extension=file.filename.split('.')[-1]
                file_data=file.read()
                cursor.execute('insert into files(file_id,file_extension,data,addedby) values(uuid_to_bin(uuid()),%s,%s,%s)',[file_extension,file_data,addedby])
                mydb.commit()
                cursor.close()
                flash('your file  successfully added')
                return redirect(url_for('home'))
    return render_template('file.html')
@app.route('/file')
def file():
    if session.get('user'):
        addedby=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(file_id),file_extension,date from files where addedby=%s',[addedby])
        count=cursor.fetchall()
        return render_template('data.html',count=count)
    return redirect(url_for('login'))
@app.route('/viewfile/<fid>',methods=['GET','POST'])
def viewfile(fid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select file_extension,data from files where file_id=uuid_to_bin(%s)',[fid])
        ext,data=cursor.fetchone()
        data=BytesIO(data)
        filename=f'attachment.{ext}'
        return send_file(data,download_name=filename,as_attachment=False)
    return render_template('viewfile.html',data)
@app.route('/download/<fid>')
def download(fid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select file_extension,data from files where file_id=uuid_to_bin(%s)',[fid])
        ext,data=cursor.fetchone()
        data=BytesIO(data)
        filename=f'attachment.{ext}'
        return send_file(data,download_name=filename,as_attachment=True)
    return redirect(url_for('file'))
@app.route('/fdelete/<fid>')
def fdelete(fid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('delete from files where file_id=uuid_to_bin(%s)',[fid])
    mydb.commit()
    cursor.close()
    return redirect(url_for('home'))
app.run(debug=True,use_reloader=True)