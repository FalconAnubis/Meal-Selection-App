import streamlit as st
import datetime
import random
import json
import pandas as pd
from datetime import timedelta

# --- CONFIGURATION & DATA STORAGE ---
DATA_FILE = 'dinner_data.json'

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Default Data Structure
        return {
            "history": [], # List of {date: str, meat: str, side: str, category: str}
            "current_month_plan": [], 
            "categories": {
                "Chicken": ["Grilled Chicken", "Chicken Parm", "Curry", "Stir Fry"],
                "Beef": ["Steak", "Burgers", "Meatloaf", "Roast"],
                "Pork": ["Pork Chops", "Pulled Pork", "Ham"],
                "Fish": ["Salmon", "Tilapia", "Shrimp Scampi"],
                "Pasta": ["Spaghetti", "Alfredo", "Lasagna"],
                "Taco": ["Beef Tacos", "Chicken Tacos", "Fish Tacos", "Carnitas"] # Special Category
            },
            "sides": ["Rice", "Broccoli", "Side Salad", "Corn", "Mashed Potatoes", "Asparagus", "Green Beans"]
        }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- LOGIC ENGINE ---
def get_days_remaining_in_month():
    today = datetime.date.today()
    # Find the last day of the current month
    next_month = today.replace(day=28) + datetime.timedelta(days=4)
    last_day = next_month - datetime.timedelta(days=next_month.day)
    
    days_left = []
    current = today
    while current <= last_day:
        days_left.append(current)
        current += timedelta(days=1)
    return days_left

def check_constraints(date, category, item, side, data, week_category_counts):
    # 1. Category max 2 times a week
    # Get ISO week number
    week_num = date.isocalendar()[1]
    if week_category_counts.get((week_num, category), 0) >= 2:
        return False

    # Check history (Past 3 weeks for item, 2 weeks for side)
    # Convert string dates in history to objects for comparison
    history_limit_item = date - timedelta(weeks=3)
    history_limit_side = date - timedelta(weeks=2)

    for record in data['history'] + data['current_month_plan']:
        record_date = datetime.datetime.strptime(record['date'], "%Y-%m-%d").date()
        
        # Rule: No repeat item for 3 weeks
        if record['meat'] == item and record_date >= history_limit_item and record_date < date:
            return False
            
        # Rule: No repeat side for 2 weeks
        if record['side'] == side and record_date >= history_limit_side and record_date < date:
            return False
            
    return True

def generate_schedule(data):
    days = get_days_remaining_in_month()
    new_plan = []
    week_category_counts = {} # Key: (week_num, category), Value: count
    
    # Pre-fill specific constraints based on existing plan if needed
    # For now, we wipe the future plan and regenerate
    
    for day in days:
        week_num = day.isocalendar()[1]
        
        # --- TACO TUESDAY LOGIC ---
        if day.weekday() == 1: # 0 is Monday, 1 is Tuesday
            category = "Taco"
            # Rotate meat: Look at last Taco Tuesday to pick different meat
            taco_options = data['categories']['Taco']
            # Simple rotation or random choice that isn't the last one
            chosen_meat = random.choice(taco_options)
            chosen_side = "Mexican Rice" # Force side or pick random
        
        # --- STANDARD DAY LOGIC ---
        else:
            # 1. Pick Category (excluding Taco)
            valid_cats = [c for c in data['categories'].keys() if c != "Taco"]
            random.shuffle(valid_cats)
            
            category = None
            for cat in valid_cats:
                if week_category_counts.get((week_num, cat), 0) < 2:
                    category = cat
                    break
            
            if not category: category = random.choice(valid_cats) # Fallback
            
            # 2. Pick Meat & Side
            meat_options = data['categories'][category]
            side_options = data['sides']
            
            # Try to find a valid combination 50 times, otherwise force one
            chosen_meat = random.choice(meat_options)
            chosen_side = random.choice(side_options)
            
            for _ in range(50):
                m = random.choice(meat_options)
                s = random.choice(side_options)
                if check_constraints(day, category, m, s, data, week_category_counts):
                    chosen_meat = m
                    chosen_side = s
                    break

        # Record Selection
        week_category_counts[(week_num, category)] = week_category_counts.get((week_num, category), 0) + 1
        
        entry = {
            "date": day.strftime("%Y-%m-%d"),
            "day_name": day.strftime("%A"),
            "category": category,
            "meat": chosen_meat,
            "side": chosen_side
        }
        new_plan.append(entry)

    data['current_month_plan'] = new_plan
    save_data(data)
    return new_plan

# --- UI LAYOUT ---
st.set_page_config(page_title="Dinner Planner", page_icon="🍽️")
st.title("🍽️ Monthly Dinner Planner")

# Load Data
data = load_data()

# Navigation (The 4 Buttons)
menu = st.radio("Menu", ["Generate", "This Month", "Edit Meals", "Send Out List"], horizontal=True)

if menu == "Generate":
    st.header("Generate Schedule")
    st.write(f"Generate meals for the rest of {datetime.date.today().strftime('%B')}.")
    
    if st.button("Generate New List", type="primary"):
        with st.spinner("Cooking up a schedule..."):
            plan = generate_schedule(data)
        st.success("Menu Generated!")
        st.dataframe(pd.DataFrame(plan)[['day_name', 'date', 'meat', 'side']])

elif menu == "This Month":
    st.header("This Month's Schedule")
    if not data['current_month_plan']:
        st.info("No plan generated yet.")
    else:
        df = pd.DataFrame(data['current_month_plan'])
        # Display as a clean table
        st.table(df[['day_name', 'date', 'meat', 'side']])

elif menu == "Edit Meals":
    st.header("Edit Database")
    
    # Edit Categories and Items
    st.subheader("Categories & Meats")
    cat_to_edit = st.selectbox("Select Category", list(data['categories'].keys()))
    
    # Text area to edit items (comma separated)
    current_items = ", ".join(data['categories'][cat_to_edit])
    new_items_str = st.text_area(f"Items for {cat_to_edit} (comma separated)", current_items)
    
    if st.button("Save Items"):
        new_list = [x.strip() for x in new_items_str.split(",")]
        data['categories'][cat_to_edit] = new_list
        save_data(data)
        st.success(f"Saved {cat_to_edit}!")

    # Edit Sides
    st.subheader("Sides")
    current_sides = ", ".join(data['sides'])
    new_sides_str = st.text_area("Sides (comma separated)", current_sides)
    if st.button("Save Sides"):
        new_list = [x.strip() for x in new_sides_str.split(",")]
        data['sides'] = new_list
        save_data(data)
        st.success("Sides Updated!")

elif menu == "Send Out List":
    st.header("Send Out List")
    if not data['current_month_plan']:
        st.warning("Generate a list first.")
    else:
        # Format the text message
        msg_lines = ["Here is the dinner menu for the rest of the month:"]
        for meal in data['current_month_plan']:
            msg_lines.append(f"{meal['date']} ({meal['day_name']}): {meal['meat']} with {meal['side']}")
        
        final_msg = "\n".join(msg_lines)
        
        st.text_area("Copy this text:", final_msg, height=300)
        
        # Link for Mobile SMS
        # Note: formatting newlines in HTML links is tricky, using %0a
        import urllib.parse
        encoded_msg = urllib.parse.quote(final_msg)
        st.markdown(f'''<a href="sms:&body={encoded_msg}"><button style="
            background-color:#4CAF50;
            color: white;
            padding: 10px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;">
            Open in Messages App
            </button></a>''', unsafe_allow_html=True)