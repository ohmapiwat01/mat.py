import streamlit as st
import sqlite3
import pandas as pd
import math
from fpdf import FPDF
import datetime
import streamlit_authenticator as stauth
import requests

# --- CONFIGURATION ---
st.set_page_config(page_title="Material Store Pro", layout="wide", page_icon="🏗️")

# --- 1. FUNCTION: PDF GENERATION (PROFESSIONAL LAYOUT) ---
# แก้ไข: เพิ่มพารามิเตอร์ area_info เพื่อรับค่าขนาดพื้นที่
def export_pdf(job, calc_details, total_price, customer_name, area_info):
    pdf = FPDF()
    pdf.add_page()
    
    # เพิ่มฟอนต์ภาษาไทย
    try:
        pdf.add_font('THSarabun', '', 'THSarabunNew.ttf')
        pdf.set_font('THSarabun', '', 16)
        font_name = 'THSarabun'
    except:
        pdf.set_font('Arial', size=12)
        font_name = 'Arial'

    # ส่วนหัวเอกสาร
    pdf.set_font(font_name, size=22)
    pdf.cell(0, 10, "ใบเสนอราคา / QUOTATION", ln=True, align='C')
    pdf.set_font(font_name, size=14)
    pdf.cell(0, 10, "Material Store Pro - ร้านจำหน่ายวัสดุก่อสร้าง", ln=True, align='C')
    pdf.line(10, 32, 200, 32)
    pdf.ln(10)

    # ข้อมูลลูกค้าและวันที่
    pdf.set_font(font_name, size=14)
    pdf.cell(100, 8, f"ชื่อลูกค้า: {customer_name}")
    pdf.cell(90, 8, f"วันที่เสนอราคา: {datetime.date.today().strftime('%d/%m/%Y')}", ln=True, align='R')
    pdf.cell(0, 8, f"ประเภทงาน: {job}", ln=True)
    
    # แก้ไข: เพิ่มการแสดงขนาดพื้นที่ใต้ประเภทงาน
    area_text = f"รายละเอียดพื้นที่: กว้าง {area_info['w']} ม. x ยาว {area_info['l']} ม. x หนา {area_info['t']} ม. (เผื่อเสีย {area_info['waste']}%)"
    pdf.set_text_color(0, 0,0) 
    pdf.cell(0, 8, area_text, ln=True)
    pdf.set_text_color(0, 0, 0) # กลับเป็นสีดำ
    pdf.ln(5)

    # ตารางรายการสินค้า
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font(font_name, size=14)
    pdf.cell(80, 10, " รายการวัสดุ", border=1, fill=True)
    pdf.cell(30, 10, "จำนวน", border=1, fill=True, align='C')
    pdf.cell(30, 10, "หน่วย", border=1, fill=True, align='C')
    pdf.cell(50, 10, "รวมเงิน (บาท)", border=1, fill=True, align='C', ln=True)

    # เนื้อหาในตาราง
    pdf.set_font(font_name, size=14)
    for item in calc_details:
        pdf.cell(80, 10, f" {item['name']}", border=1)
        pdf.cell(30, 10, f"{item['qty']:,.2f}", border=1, align='C')
        pdf.cell(30, 10, item['unit'], border=1, align='C')
        pdf.cell(50, 10, f"{item['subtotal']:,.2f}", border=1, align='R', ln=True)

    # สรุปราคาสุทธิ
    pdf.ln(2)
    pdf.set_font(font_name, size=16)
    pdf.cell(140, 10, "ราคารวมสุทธิทั้งสิ้น (Total): ", border=0, align='R')
    pdf.cell(50, 10, f"{total_price:,.2f} บาท ", border=1, align='R', ln=True)

    # ส่วนลงชื่อ
    pdf.ln(20)
    pdf.set_font(font_name, size=12)
    pdf.cell(95, 10, "ลงชื่อ: __________________________", align='C')
    pdf.cell(95, 10, "ลงชื่อ: __________________________", align='C', ln=True)
    pdf.cell(95, 10, "(ผู้เสนอราคา)", align='C')
    pdf.cell(95, 10, "(ลูกค้า)", align='C', ln=True)

    return pdf.output()

# --- 2. FUNCTION: LINE NOTIFY ---
def send_line_notify(message):
    token = "YOUR_LINE_TOKEN" # ใส่ Token ของคุณที่นี่
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": "Bearer " + token}
    data = {"message": message}
    try:
        requests.post(url, headers=headers, data=data)
    except:
        pass

# --- 3. DATABASE MANAGEMENT ---
def init_db():
    conn = sqlite3.connect('store_data.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY, name TEXT, discount REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, item TEXT, total REAL, date TEXT)')
    
    c.execute("SELECT count(*) FROM products")
    if c.fetchone()[0] == 0:
        items = [('ปูนซีเมนต์ (ถุง)', 145.0), ('ทรายหยาบ (คิว)', 550.0), ('หิน 3/4 (คิว)', 600.0)]
        c.executemany("INSERT INTO products (name, price) VALUES (?, ?)", items)
    conn.commit()
    conn.close()

def get_db(): return sqlite3.connect('store_data.db')
init_db()

# --- 4. AUTHENTICATION ---
users = {'usernames': {
    'admin': {'name': 'ผู้จัดการร้าน', 'password': '123'},
    'user': {'name': 'พนักงานขาย', 'password': '0123'}
}}

authenticator = stauth.Authenticate(users, 'store_v1', 'auth_key', cookie_expiry_days=1)
name, auth_status, username = authenticator.login('main')

if auth_status:
    authenticator.logout('ออกจากระบบ', 'sidebar')
    st.sidebar.title(f"👤 {name}")
    
    menu = st.sidebar.selectbox("เมนูควบคุม", 
                                ["📊 Dashboard", "🧮 คำนวณวัสดุ", "⚙️ จัดการราคา/สมาชิก"] if username == 'admin' else ["🧮 คำนวณวัสดุ"])

    # --- PAGE: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.header("📈 สรุปภาพรวมของร้าน")
        df_logs = pd.read_sql("SELECT * FROM logs", get_db())
        if not df_logs.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("ยอดคำนวณแบ่งตามงาน")
                st.bar_chart(df_logs['item'].value_counts())
            with c2:
                st.subheader("แนวโน้มยอดเสนอราคา")
                df_logs['date'] = pd.to_datetime(df_logs['date'])
                st.line_chart(df_logs.set_index('date')['total'])
        else:
            st.info("ยังไม่มีข้อมูลในระบบ")

    # --- PAGE: CALCULATION ---
    elif menu == "🧮 คำนวณวัสดุ":
        st.header("🏗️ คำนวณปริมาณปูน ทราย หิน")
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                job = st.selectbox("ลักษณะงาน", ["เทพื้น 1:2:4", "เทพื้นหยาบ 1:3:6", "ก่อ/ฉาบ 1:3"])
                w = st.number_input("กว้าง (ม.)", value=1.0, min_value=0.1)
                l = st.number_input("ยาว (ม.)", value=1.0, min_value=0.1)
            with col2:
                member_df = pd.read_sql("SELECT name FROM members", get_db())
                member = st.selectbox("ลูกค้า/สมาชิก", ["ลูกค้าทั่วไป"] + member_df['name'].tolist())
                t = st.number_input("หนา (ม.)", value=0.1, min_value=0.01)
                waste = st.slider("เผื่อเสีย (%)", 0, 15, 5)

        if st.button("🚀 คำนวณและออกใบเสนอราคา", use_container_width=True):
            # สูตรคำนวณ
            vol = (w * l * t) * (1 + waste/100)
            dry_vol = vol * 1.54
            r = (1,2,4) if "1:2:4" in job else (1,3,6) if "1:3:6" in job else (1,3,0)
            
            p_data = pd.read_sql("SELECT * FROM products", get_db()).set_index('name')
            
            c_bag = math.ceil(((r[0]/sum(r)) * dry_vol * 1440) / 50)
            s_m3 = (r[1]/sum(r)) * dry_vol
            st_m3 = (r[2]/sum(r)) * dry_vol if r[2] > 0 else 0
            
            # เตรียมข้อมูลสำหรับ PDF และคำนวณราคารายชิ้น
            calc_details = [
                {"name": "ปูนซีเมนต์ (ถุง)", "qty": c_bag, "unit": "ถุง", "subtotal": c_bag * p_data.at['ปูนซีเมนต์ (ถุง)', 'price']},
                {"name": "ทรายหยาบ (คิว)", "qty": s_m3, "unit": "คิว", "subtotal": s_m3 * p_data.at['ทรายหยาบ (คิว)', 'price']},
                {"name": "หิน 3/4 (คิว)", "qty": st_m3, "unit": "คิว", "subtotal": st_m3 * p_data.at['หิน 3/4 (คิว)', 'price']}
            ]
            
            total_price = sum(item['subtotal'] for item in calc_details)
            
            # บันทึกลง Log
            conn = get_db()
            conn.execute("INSERT INTO logs (item, total, date) VALUES (?, ?, ?)", 
                         (job, total_price, datetime.date.today().isoformat()))
            conn.commit()
            conn.close()
            
            # แสดงผลลัพธ์
            st.success(f"คำนวณเสร็จสิ้นสำหรับงาน: {job}")
            c_res1, c_res2, c_res3 = st.columns(3)
            c_res1.metric("ปูน", f"{c_bag} ถุง")
            c_res2.metric("ทราย", f"{s_m3:.2f} คิว")
            c_res3.metric("หิน", f"{st_m3:.2f} คิว")
            
            st.subheader(f"💰 ราคารวมสุทธิ: {total_price:,.2f} บาท")
            
            # แก้ไข: เตรียมข้อมูลขนาดพื้นที่ส่งไปยังฟังก์ชัน PDF
            area_info = {"w": w, "l": l, "t": t, "waste": waste}
            pdf_bytes = export_pdf(job, calc_details, total_price, member, area_info)
            
            st.download_button(
                label="📥 ดาวน์โหลดใบเสนอราคา (PDF)",
                data=bytes(pdf_bytes),
                file_name=f"Quotation_{member}_{datetime.date.today()}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
            send_line_notify(f"\n📢 ออกใบเสนอราคาใหม่!\nลูกค้า: {member}\nงาน: {job}\nยอดรวม: {total_price:,.2f} บาท")

    # --- PAGE: ADMIN SETTINGS ---
    elif menu == "⚙️ จัดการราคา/สมาชิก":
        st.header("🛠️ ตั้งค่าระบบ (เฉพาะ Admin)")
        tab1, tab2 = st.tabs(["ราคาสินค้า", "สมาชิก"])
        with tab1:
            df_p = pd.read_sql("SELECT * FROM products", get_db())
            new_p = st.data_editor(df_p, use_container_width=True)
            if st.button("💾 บันทึกราคา"):
                conn = get_db()
                new_p.to_sql('products', conn, if_exists='replace', index=False)
                st.success("อัปเดตราคาสำเร็จ!")
        with tab2:
            m_name = st.text_input("ชื่อสมาชิกใหม่")
            if st.button("➕ เพิ่มรายชื่อ"):
                conn = get_db()
                conn.execute("INSERT INTO members (name, discount) VALUES (?, 0)", (m_name,))
                conn.commit()
                st.rerun()

elif auth_status is False:
    st.error('รหัสผ่านไม่ถูกต้อง')