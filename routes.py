from app import app, db, login_manager, mail
from flask import (render_template, request, redirect, send_file, flash, url_for)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import User, Patient, Doctor, Medicine, Bill, LabReport

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from flask_mail import Message

import os
import io
import re

if not os.path.exists('static/uploads'):os.makedirs('static/uploads')
# Load user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Home
@app.route('/')
def home():
    return render_template('home.html')


# Register
import re

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
    
        if User.query.filter_by(email=email).first():
            flash("Email already exists", "danger")
            return redirect('/register')
        
        if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$', password):
            flash("Password must contain uppercase, lowercase, number & 8+ chars", "danger")
            return redirect('/register')

        user = User(
            hospital_name=request.form['hospital'],
            email=email,
            password=generate_password_hash(password),
            role=request.form['role']
        )

        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect('/login')

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect('/dashboard')
        
        # flash message for wrong Credentials 
        flash('Invalid email or password', 'danger')
        return redirect('/login')

    return render_template('login.html')


# Dashboard (protected)
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template(
        'dashboard.html',
        patients=Patient.query.all(),
        medicines=Medicine.query.all(),
        reports=LabReport.query.all(),
        bills=Bill.query.all()
    )


# Logout 
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

#Patient Page
@app.route('/patients')
@login_required
def patients():
    all_patients = Patient.query.all()
    return render_template('patients.html', patients=all_patients)

#Add patient route
@app.route('/add_patient', methods=['POST'])
@login_required
def add_patient():
    patient = Patient(
        first_name=request.form['first_name'],
        last_name=request.form['last_name'],
        age=request.form['age'],
        gender=request.form['gender'],
        guardian_name=request.form['guardian'],
        email=request.form['email'],
        phone=request.form['phone'],
        address=request.form['address']
    )

    db.session.add(patient)
    db.session.commit()

    return redirect('/patients')

#Doctor
@app.route('/doctors')
@login_required
def doctors():
    all_doctors = Doctor.query.all()
    return render_template('doctors.html', doctors=all_doctors)


#add doctor
@app.route('/add_doctor', methods=['POST'])
@login_required
def add_doctor():
    doctor = Doctor(
        name=request.form['name'],
        specialization=request.form['specialization'],
        fee=request.form['fee']
    )

    db.session.add(doctor)
    db.session.commit()

    return redirect('/doctors')

#edit doctor
@app.route('/edit_doctor/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_doctor(id):
    doctor = Doctor.query.get(id)

    if request.method == 'POST':
        doctor.name = request.form['name']
        doctor.specialization = request.form['specialization']
        doctor.fee = request.form['fee']

        db.session.commit()
        return redirect('/doctors')

    return render_template('edit_doctor.html', doctor=doctor)

#medicines
@app.route('/medicines')
@login_required
def medicines():
    if current_user.role != 'pharmacist':
        return "Access Denied"
    all_medicines = Medicine.query.all()
    return render_template('medicines.html', medicines=all_medicines)

#add medicines
@app.route('/add_medicine', methods=['POST'])
@login_required
def add_medicine():
    medicine = Medicine(
        name=request.form['name'],
        description=request.form['description'],
        price=request.form['price'],
        quantity=request.form['quantity']
    )

    db.session.add(medicine)
    db.session.commit()

    return redirect('/medicines')


#edit medicines
@app.route('/edit_medicine/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_medicine(id):
    medicine = Medicine.query.get(id)

    if request.method == 'POST':
        medicine.name = request.form['name']
        medicine.price = request.form['price']

        db.session.commit()
        return redirect('/medicines')

    return render_template('edit_medicine.html', medicine=medicine)

#billing
@app.route('/billing', methods=['GET', 'POST'])
@login_required
def billing():
    patients = Patient.query.all()
    doctors = Doctor.query.all()
    medicines = Medicine.query.all()
    reports = LabReport.query.all()

    if request.method == 'POST':

        patient_id = request.form['patient_id']
        medicines_data = request.form.getlist('medicines')
        reports_data = request.form.getlist('reports')
        total = request.form['total']

        bill = Bill(
            patient_id=patient_id,
            medicines=json.dumps(medicines_data),
            reports=json.dumps(reports_data),
            total=total,
            status='draft',
            created_by=current_user.role
        )

        db.session.add(bill)
        db.session.commit()

        return redirect('/dashboard')

    return render_template(
        'billing.html',
        patients=patients,
        doctors=doctors,
        medicines=medicines,
        reports=reports
    )

#billing process
import json



import json

import json

@app.route('/create_bill', methods=['POST'])
@login_required
def create_bill():

    # ✅ FIRST: Validate patient selection
    if not request.form.get('patient'):
        flash("Please select patient", "danger")
        return redirect('/billing')

    # ✅ THEN safely assign
    patient_id = request.form.get('patient')

    # safer role matching
    role = (current_user.role or "").strip().lower()


    # --------------------------------
    # PHARMACIST DRAFT BILL
    # --------------------------------
    if role in ['pharmacist','pharmacy']:

        medicine_ids = request.form.getlist('medicines')

        medicines_data = []
        total = 0

        for m_id in medicine_ids:

            med = Medicine.query.get(m_id)

            qty = int(request.form.get(f'qty_{m_id}', 1))

            if med and med.quantity >= qty:

                med.quantity -= qty

                line_total = med.price * qty

                medicines_data.append({
                    'name': med.name,
                    'price': med.price,
                    'qty': qty,
                    'subtotal': line_total
                })

                total += line_total

        # ✅ Optional improvement
        if len(medicines_data) == 0:
            flash("Please select at least one medicine", "danger")
            return redirect('/billing')

        bill = Bill(
            patient_id=patient_id,
            medicines=json.dumps(medicines_data),
            reports="[]",
            total=total,
            status='draft',
            created_by='pharmacist'
        )


    # --------------------------------
    # LAB WORKER DRAFT BILL
    # --------------------------------
    elif role in ['lab','lab_administrative']:

        report_ids = request.form.getlist('reports')

        reports_data = []
        total = 0

        for r_id in report_ids:

            rep = LabReport.query.get(r_id)

            if rep:
                reports_data.append({
                    'name': rep.name,
                    'fee': rep.fee
                })

                total += rep.fee

        if request.form.get('insurance'):
            total *= 0.7

        # ✅ Optional improvement
        if len(reports_data) == 0:
            flash("Please select at least one lab report", "danger")
            return redirect('/billing')

        bill = Bill(
            patient_id=patient_id,
            medicines="[]",
            reports=json.dumps(reports_data),
            total=total,
            status='draft',
            created_by='lab'
        )


    # --------------------------------
    # ADMIN FINAL BILL
    # --------------------------------
    elif role == 'admin':

        medicine_ids = request.form.getlist('medicines')
        report_ids = request.form.getlist('reports')

        medicines_data = []
        reports_data = []

        total = float(request.form.get('total', 0))

        doctor_id = request.form.get('doctor')

        doctor_name = ""
        doctor_fee = 0

        if doctor_id:
            doctor = Doctor.query.get(doctor_id)
            if doctor:
                doctor_name = doctor.name
                doctor_fee = doctor.fee
                total += doctor_fee

        for m_id in medicine_ids:
            med = Medicine.query.get(m_id)
            qty = int(request.form.get(f'qty_{m_id}', 1))

            if med and med.quantity >= qty:
                med.quantity -= qty

                line_total = med.price * qty

                medicines_data.append({
                    'name': med.name,
                    'price': med.price,
                    'qty': qty,
                    'subtotal': line_total
                })

                total += line_total

        for r_id in report_ids:
            rep = LabReport.query.get(r_id)
            if rep:
                reports_data.append({
                    'name': rep.name,
                    'fee': rep.fee
                })
                total += rep.fee

        if request.form.get('insurance'):
            total *= 0.7

        bill = Bill(
            patient_id=patient_id,
            medicines=json.dumps(medicines_data),
            reports=json.dumps(reports_data),
            total=total,
            status='pending',
            created_by='admin',
            doctor_name=doctor_name,
            doctor_fee=doctor_fee
        )

    else:
        return redirect('/login')


    db.session.add(bill)
    db.session.commit()


    # role based redirects
    if role in ['pharmacist','pharmacy']:
        flash('Medicine draft sent to admin successfully', 'success')
        return redirect('/dashboard')

    if role in ['lab','lab_administrative']:
        flash('Lab report draft sent to admin successfully', 'success')
        return redirect('/dashboard')

    return redirect('/invoice/' + str(bill.id))

@app.route('/upload_logo', methods=['POST'])
@login_required
def upload_logo():
    file = request.files['logo']

    if file:
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        current_user.logo = filename
        db.session.commit()

    return redirect('/dashboard')



#download PDF
@app.route('/download_pdf/<int:id>')
@login_required
def download_pdf(id):

    import json
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    )
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    bill = Bill.query.get_or_404(id)
    if bill.created_by != current_user.role and current_user.role != 'admin':
        return "Unauthorized Access"
    patient = Patient.query.get(bill.patient_id)

    medicines = json.loads(bill.medicines or "[]")
    reports = json.loads(bill.reports or "[]")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'title',
        fontSize=16,
        leading=20,
        spaceAfter=10,
        alignment=1
    )

    section_style = ParagraphStyle(
        'section',
        fontSize=12,
        spaceAfter=6,
        textColor=colors.black,
        leading=14
    )

    elements = []

    # ---------------- HEADER ---------------- #

    logo = ""
    if current_user.logo:
        try:
            logo = Image(f"static/uploads/{current_user.logo}",
                         width=1.2*inch, height=1.2*inch)
        except:
            logo = ""

    hospital_info = Paragraph(
        f"""
        <b>{current_user.hospital_name}</b><br/>
        Premium Multispeciality Hospital<br/>
        Address: Ahmedabad, India<br/>
        """,
        styles['Normal']
    )

    header = Table([[logo, hospital_info]],
                   colWidths=[1.5*inch, 4.5*inch])

    elements.append(header)
    elements.append(Spacer(1, 15))

    # ---------------- INVOICE TITLE ---------------- #

    invoice_no = f"HOS-{bill.id:05d}"

    elements.append(Paragraph(
        f"<b>INVOICE</b><br/><font size=10>Invoice No: {invoice_no}</font>",
        title_style
    ))

    elements.append(Spacer(1, 10))

    # ---------------- PATIENT ---------------- #

    date_text = (
        bill.created_at.strftime('%d %b %Y, %I:%M %p')
        if hasattr(bill, "created_at") and bill.created_at
        else "N/A"
    )

    info_table = Table([
        ["Patient Name", f"{patient.first_name} {patient.last_name}",
         "Date", date_text],
        ["Phone", patient.phone,
         "Status", bill.status.upper()]
    ], colWidths=[1.5*inch, 2.5*inch, 1.2*inch, 2*inch])

    info_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6'))
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # ---------------- MEDICINES ---------------- #

    medicine_total = 0

    if medicines:
        elements.append(Paragraph("<b>Medicines</b>", section_style))

        data = [["Medicine", "Qty", "Rate", "Amount"]]

        for m in medicines:
            data.append([
                m['name'],
                str(m['qty']),
                f"{m['price']}",
                f"{m['subtotal']}"
            ])
            medicine_total += m['subtotal']

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dbeafe'))
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

    # ---------------- REPORTS ---------------- #

    report_total = 0

    if reports:
        elements.append(Paragraph("<b>Lab Reports</b>", section_style))

        data = [["Test", "Fee"]]

        for r in reports:
            data.append([r['name'], f"{r['fee']}"])
            report_total += r['fee']

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#fee2e2'))
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

    # ---------------- DOCTOR ---------------- #

    if bill.doctor_name:
        elements.append(Paragraph("<b>Doctor Consultation</b>", section_style))

        doc_table = Table([
            ["Doctor", f"Dr. {bill.doctor_name}"],
            ["Consultation Fee", f"{bill.doctor_fee}"]
        ])

        doc_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey)
        ]))

        elements.append(doc_table)
        elements.append(Spacer(1, 20))

    # ---------------- TOTAL ---------------- #

    subtotal = medicine_total + report_total
    gst = subtotal * 0.18
    final_total = bill.total

    total_table = Table([
        ["Subtotal", f"{subtotal}"],
        ["GST (18%)", f"{gst:.2f}"],
        ["Doctor Fee", f"{bill.doctor_fee}"],
        ["Grand Total", f"{final_total}"]
    ], colWidths=[3*inch, 2*inch])

    total_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1.2, colors.black),
        ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#d1fae5'))
    ]))

    elements.append(total_table)
    elements.append(Spacer(1, 30))

    # ---------------- SIGNATURE ---------------- #

    sign_table = Table([
        ["Prepared By", "Authorized Signatory"],
        ["__________________", "__________________"]
    ], colWidths=[3*inch, 3*inch])

    elements.append(sign_table)
    elements.append(Spacer(1, 20))

    # ---------------- FOOTER ---------------- #

    elements.append(Paragraph(
        "This is a computer-generated invoice.<br/>"
        "Thank you for trusting our healthcare services.",
        styles['Italic']
    ))

    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Invoice_{invoice_no}.pdf"
    )

#lab report
@app.route('/lab_reports')
@login_required
def lab_reports():

    if current_user.role not in ['lab', 'lab_administrative']:
        return "Access Denied"

    reports = LabReport.query.all()

    return render_template('lab_reports.html', reports=reports) 

#add reports

@app.route('/add_report', methods=['POST'])
@login_required
def add_report():
    report = LabReport(
        name=request.form['name'],
        description=request.form['description'],
        fee=request.form['fee']
    )

    db.session.add(report)
    db.session.commit()

    return redirect('/lab_reports')

#edit report
@app.route('/edit_report/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_report(id):
    report = LabReport.query.get(id)

    if request.method == 'POST':
        report.name = request.form['name']
        report.fee = request.form['fee']

        db.session.commit()
        return redirect('/lab_reports')

    return render_template('edit_report.html', report=report)


#send_mail
@app.route('/send_email/<int:id>')
@login_required
def send_email(id):

    bill = Bill.query.get_or_404(id)
    patient = Patient.query.get(bill.patient_id)

    if not patient.email:
        flash("Patient email not found", "warning")
        return redirect(f'/invoice/{id}')

    try:
        msg = Message(
            'Hospital Invoice',
            sender=app.config['MAIL_USERNAME'],
            recipients=[patient.email]
        )

        msg.body = f"""
Hello {patient.first_name},

Your hospital invoice #{bill.id}
Amount: ₹{bill.total}

Thank you.
"""

        mail.send(msg)

        flash("Invoice emailed successfully", "success")

    except Exception as e:
        print("MAIL ERROR:", e)
        flash("Email failed to send (Check SMTP settings)", "danger")

    return redirect(f'/invoice/{id}')

#delete medicine 

@app.route('/delete_medicine/<int:id>')
@login_required
def delete_medicine(id):
    if current_user.role != 'pharmacist':
        return "Unauthorized"
    medicine = Medicine.query.get(id)

    db.session.delete(medicine)
    db.session.commit()

    return redirect('/medicines')


#delete lab report 

@app.route('/delete_report/<int:id>')
@login_required
def delete_report(id):
    if current_user.role not in ['lab','lab_administrative']:
        return "Unauthorized"
    report = LabReport.query.get(id)
    db.session.delete(report)
    db.session.commit()
    return redirect('/lab_reports')


#pending bill approval
@app.route('/pending_bills')
@login_required
def pending_bills():

    if current_user.role != 'admin':
        return "Unauthorized"

    drafts = Bill.query.filter_by(
        status='draft'
    ).all()

    return render_template(
        'pending_bills.html',
        bills=drafts
    )

#approve bill route 
@app.route('/approve_bill/<int:id>')
@login_required
def approve_bill(id):
    bill = Bill.query.get(id)
    bill.status = 'completed'
    db.session.commit()
    return redirect('/bill_history')


#bill history
@app.route('/bill_history')
@login_required
def bill_history():

    bills = Bill.query.filter_by(status='completed').all()

    # attach patient data
    data = []
    for b in bills:
        patient = Patient.query.get(b.patient_id)

        data.append({
            "id": b.id,
            "total": b.total,
            "date": getattr(b, "created_at", None),  # if you add date field
            "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
        })

    return render_template('bill_history.html', bills=data)



#send bill to admin 
@app.route('/send_to_admin/<int:id>')
@login_required
def send_to_admin(id):
    bill = Bill.query.get(id)
    bill.status = 'pending'
    db.session.commit()
    return redirect('/dashboard')


#invoice 
import json
@app.route('/invoice/<int:id>', methods=['GET','POST'])
@login_required
def invoice(id):

    bill = Bill.query.get_or_404(id)
    if bill.created_by != current_user.role and current_user.role != 'admin':
        return "Unauthorized Access"
 
    patient = Patient.query.get(
        bill.patient_id
    )

    medicines = json.loads(
        bill.medicines or "[]"
    )

    reports = json.loads(
        bill.reports or "[]"
    )

    doctors = Doctor.query.all()


    medicine_total = sum(
        x.get('subtotal',0)
        for x in medicines
    )

    report_total = sum(
        x.get('fee',0)
        for x in reports
    )


    if request.method=="POST":

        doctor_id=request.form.get(
            "doctor"
        )

        if doctor_id:

            doctor=Doctor.query.get(
                doctor_id
            )

            if doctor:
                bill.doctor_name=doctor.name
                bill.doctor_fee=doctor.fee


        bill.total=(
            medicine_total
            + report_total
            + bill.doctor_fee
        )

        bill.status="completed"

        db.session.commit()

        flash(
          "Final bill generated",
          "success"
        )

        return redirect(
          f'/invoice/{bill.id}'
        )


    final_estimate=(
        medicine_total
        + report_total
        + (bill.doctor_fee or 0)
    )


    return render_template(
        'invoice.html',
        bill=bill,
        patient=patient,
        medicines=medicines,
        reports=reports,
        doctors=doctors,
        medicine_total=medicine_total,
        report_total=report_total,
        final_estimate=final_estimate
    )
#combine BIlls

import json

@app.route('/combine_bills', methods=['POST'])
@login_required
def combine_bills():

    if current_user.role!='admin':
        return "Unauthorized"

    selected_ids=request.form.getlist(
       'bill_ids'
    )

    if not selected_ids:
        flash(
        "Select bills first",
        "warning"
        )
        return redirect(
         '/pending_bills'
        )


    bills=Bill.query.filter(
      Bill.id.in_(selected_ids)
    ).all()


    first_patient=bills[0].patient_id

    meds=[]
    reports=[]
    grand_total=0


    for b in bills:

        if b.patient_id!=first_patient:
            return "Only same patient bills allowed"

        meds.extend(
         json.loads(
          b.medicines or "[]"
         )
        )

        reports.extend(
         json.loads(
          b.reports or "[]"
         )
        )

        grand_total+=b.total


    combined=Bill(
      patient_id=first_patient,
      medicines=json.dumps(meds),
      reports=json.dumps(reports),
      total=grand_total,
      status='pending',
      created_by='admin'
    )


    db.session.add(combined)

    for b in bills:
        db.session.delete(b)

    db.session.commit()

    return redirect(
      f'/invoice/{combined.id}'
    )


#final_bill
@app.route('/final_bill/<int:id>',methods=['GET','POST'])
@login_required
def final_bill(id):

    bill=Bill.query.get(id)

    doctors=Doctor.query.all()

    if request.method=='POST':

        doctor=Doctor.query.get(
            request.form['doctor']
        )

        bill.doctor_name=doctor.name
        bill.doctor_fee=doctor.fee

        bill.total += doctor.fee

        bill.status='completed'

        db.session.commit()

        return redirect(
           f'/invoice/{bill.id}'
        )

    return render_template(
       'final_bill.html',
       bill=bill,
       doctors=doctors
    )