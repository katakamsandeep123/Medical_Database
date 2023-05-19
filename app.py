import sqlite3
import streamlit as st
import base64
import pandas as pd
import datetime
import csv
import os
from fpdf import FPDF

# Connect to the SQLite database
conn = sqlite3.connect('medicine.db')
c = conn.cursor()

# Create a table to store medicine information
c.execute('''CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dosage TEXT,
                manufacturer TEXT,
                price REAL,
                quantity INTEGER
            )''')

# Function to add a new medicine
def add_medicine(name, dosage, manufacturer, price, quantity):
    c.execute('''INSERT INTO medicines (name, dosage, manufacturer, price, quantity)
                VALUES (?, ?, ?, ?, ?)''', (name, dosage, manufacturer, price, quantity))
    conn.commit()

# Function to retrieve all medicines
def get_all_medicines():
    c.execute("SELECT * FROM medicines")
    return c.fetchall()

# Function to delete a medicine
def delete_medicine(medicine_id):
    c.execute("DELETE FROM medicines WHERE id=?", (medicine_id,))
    conn.commit()

# Function to update medicine quantity
def update_medicine_quantity(medicine_id, quantity, increment=True):
    c.execute("SELECT quantity FROM medicines WHERE id=?", (medicine_id,))
    current_quantity = c.fetchone()[0]
    new_quantity = current_quantity + quantity if increment else current_quantity - quantity
    c.execute("UPDATE medicines SET quantity=? WHERE id=?", (new_quantity, medicine_id))
    conn.commit()

# Function to record daily sales
def record_daily_sales(medicines, quantities, additional_info):
    today = datetime.date.today()
    filename = f"sales_{today}.csv"

    # If the file doesn't exist, create it and write the header
    if not os.path.isfile(filename):
        with open(filename, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['ID', 'Name', 'Dosage', 'Manufacturer', 'Price', 'Quantity', 'Additional Info'])

    # Append the medicine purchase information to the file
    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        for i, medicine in enumerate(medicines):
            writer.writerow((medicine[0], medicine[1], medicine[2], medicine[3], medicine[4], quantities[i], additional_info))

    return filename

# Function to generate PDF invoice
def generate_invoice(medicines, quantities, additional_info):
    pdf = FPDF()
    pdf.add_page()

    # Set style for invoice
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Invoice Bill", ln=True, align="C")

    # Set style for table header
    pdf.set_font("Arial", "B", 10)
    pdf.cell(40, 10, "Medicine Name", 1, 0, "C")
    pdf.cell(30, 10, "Quantity", 1, 0, "C")
    pdf.cell(30, 10, "Price", 1, 1, "C")

    # Set style for table content
    pdf.set_font("Arial", "", 10)
    total_cost = 0
    for i, medicine in enumerate(medicines):
        pdf.cell(40, 10, medicine[1], 1, 0, "C")
        pdf.cell(30, 10, str(quantities[i]), 1, 0, "C")
        pdf.cell(30, 10, str(medicine[4]), 1, 1, "C")  # Price is at index 4
        total_cost += medicine[4] * quantities[i]

    # Add total cost
    pdf.cell(100, 10, "", 0, 1)
    pdf.cell(100, 10, f"Total Cost: {total_cost}", ln=True)

    # Save the PDF file
    today = datetime.date.today()
    filename = f"invoice_{today}.pdf"
    pdf.output(filename)

    return filename

# Streamlit web app
def main():
    # Set page configuration options
    st.set_page_config(
        page_title="Medicine Database",
        page_icon=":pill:",
        layout="wide"
    )

    # Add custom CSS to include background image
    page_bg_img = '''
        <style>
        body {
            background-image: url("https://www.dreamstime.com/editorial-stock-image-pharmacy-otc-products-turkey-image64209494");
            background-size: cover;
        }
        </style>
        '''
    st.markdown(page_bg_img, unsafe_allow_html=True)

    st.title("Medicine Database")

    menu = ["Add Medicine", "View All Medicines", "Delete Medicine", "Buy Medicine"]
    choice = st.sidebar.selectbox("Select Option", menu)

    if choice == "Add Medicine":
        st.subheader("Add New Medicine")
        name = st.text_input("Name")
        dosage = st.text_input("Dosage")
        manufacturer = st.text_input("Manufacturer")
        price = st.number_input("Price", min_value=0.0, value=0.0, step=0.01)
        quantity = st.number_input("Quantity", min_value=0, step=1, value=0)
        if st.button("Add", key="add_medicine"):
            add_medicine(name, dosage, manufacturer, price, quantity)
            st.success("Medicine added successfully!")

    elif choice == "View All Medicines":
        st.subheader("View All Medicines")
        medicines = get_all_medicines()
        if medicines:
            df = pd.DataFrame(medicines, columns=['ID', 'Name', 'Dosage', 'Manufacturer', 'Price', 'Quantity'])
            # Add "Update Stock" functionality within the dataframe
            update_stock_col = st.checkbox("Update Stock")
            if update_stock_col:
                selected_medicine_id = st.selectbox("Select Medicine", df['ID'], key="update_stock_select")
                quantity = st.number_input("Quantity to Add", min_value=0, step=1, value=0, key="update_stock_quantity")
                if st.button("Update", key="update_stock_button"):
                    update_medicine_quantity(selected_medicine_id, quantity)

            # Calculate the stock value (price * quantity) and add a new column
            df['Stock Value'] = df['Price'] * df['Quantity']
            st.dataframe(df)

        else:
            st.warning("No medicines found.")

    elif choice == "Delete Medicine":
        st.subheader("Delete Medicine")
        medicines = get_all_medicines()
        if medicines:
            medicine_names = [medicine[1] for medicine in medicines]  # Get only the names of medicines
            selected_medicine = st.selectbox("Select Medicine", medicine_names, key="delete_medicine_select")
            selected_medicine_info = [medicine for medicine in medicines if medicine[1] == selected_medicine][0]
            medicine_id = selected_medicine_info[0]
            if st.button("Delete", key="delete_medicine_button"):
                delete_medicine(medicine_id)
                st.success(f"Deleted medicine with ID {medicine_id}")
        else:
            st.warning("No medicines found.")

    elif choice == "Buy Medicine":
        st.subheader("Buy Medicine")
        medicines = get_all_medicines()
        if medicines:
            medicine_names = [medicine[1] for medicine in medicines]  # Get only the names of medicines
            selected_medicines = st.multiselect("Select Medicines", medicine_names, key="buy_medicine_select", help="Select the medicines to buy")
            selected_medicines_info = [medicine for medicine in medicines if medicine[1] in selected_medicines]
            quantities = []
            total_cost = 0.0

            for selected_medicine_info in selected_medicines_info:
                medicine_name = selected_medicine_info[1]
                medicine_cost = selected_medicine_info[4]  # Cost is at index 4
                quantity = st.number_input(f"Quantity of {medicine_name}", min_value=0, step=1, value=0, key=f"buy_medicine_{medicine_name}")
                quantities.append(quantity)
                total_cost += medicine_cost * quantity

            additional_info = st.text_input("Additional Information", key="buy_medicine_additional_info")
            if st.button("Buy", key="buy_medicine_button"):
                record_daily_sales(selected_medicines_info, quantities, additional_info)
                for i, selected_medicine_info in enumerate(selected_medicines_info):
                    medicine_id = selected_medicine_info[0]
                    quantity = quantities[i]
                    update_medicine_quantity(medicine_id, quantity, increment=False)
                st.success("Purchase recorded successfully!")
                st.info(f"Total Cost: {total_cost}")

                # Generate CSV file
                csv_filename = record_daily_sales(selected_medicines_info, quantities, additional_info)
                csv_button = create_download_button(csv_filename, "Download CSV")
                st.markdown("---")
                st.success("CSV file generated successfully!")
                st.markdown(csv_button, unsafe_allow_html=True)

                # Generate PDF invoice
                pdf_filename = generate_invoice(selected_medicines_info, quantities, additional_info)
                pdf_button = create_download_button(pdf_filename, "Download PDF")
                st.success("PDF invoice generated successfully!")
                st.markdown(pdf_button, unsafe_allow_html=True)

        else:
            st.warning("No medicines found.")

# Function to create a download button
def create_download_button(filename, button_text):
    with open(filename, "rb") as file:
        contents = file.read()
    encoded_file = base64.b64encode(contents).decode()
    href = f'<a href="data:file/csv;base64,{encoded_file}" download="{filename}">{button_text}</a>'
    return href

if __name__ == '__main__':
    main()
