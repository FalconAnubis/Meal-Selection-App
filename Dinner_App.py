import streamlit as st
import datetime
import random
import json
import pandas as pd
import urllib.parse
import hashlib
import os
from datetime import timedelta

# --- CONFIGURATION & PATHS ---
USER_DB_FILE = 'users.json'
PROFILE_DIR = 'profiles'

# Ensure the profile directory exists
if not os.path.exists(PROFILE_DIR):
    os.makedirs(PROFILE_DIR)

# --- SECURITY & AUTH FUNCTIONS ---

def hash_password(password):
    """Converts a password to a secure hash."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_user_db():
    try:
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {} # Returns empty dict if no users exist yet

def save_user_db(db):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

def authenticate(username, password):
    db = load_user_db()
    if username in db:
        if db[username] == hash_password(password):
            return True
    return False

def create_user(username, password):
    db = load_user_db()
    if username in db:
        return False, "Username already exists."
    
    # Save new user
    db[username] = hash_password(password)
    save_user_db(db)
    
    # Create a default data file for them
    default_data = get_default_data()
    user_file = os.path.join(PROFILE_DIR, f"{username}.json")
    with open(user_file, 'w') as f:
        json.dump(default_data, f, indent=4)
        
    return True, "User created successfully."

# --- DATA MANAGEMENT (PER USER) ---

def get_default_data():
    return {
        "history": [], 
        "current_month_plan": [], 
        "categories": {
            "Chicken": ["Chicken Wings", "Honey Garlic Chicken", "Chicken Tenders", "Chicken Stir-Fry", "Chicken Caesar", "Adobo", "Chicken Noodle Soup", "Creamy Lemon Butter Chicken", "Arroz Con Pollo"],
            "Beef": ["Korean Beef Rice Bowl", "Burgers", "Meatloaf", "Beef Sliders", "Smash Burgers", "Steak Dinner", "Meatballs", "Steak and Chimichurri"],
            "Pork": ["Pork Chops", "Pulled Pork", "Grilled Ham/Cheese", "Sausage Links", "Ribs", "Hotdogs", "Publix Deli"],
            "Others": ["Salmon", "Tilapia", "Shrimp", "Scrambled Eggs", "Omelets", "Egg Salad Sandwich", "Mac and Cheese"],
            "Veggie": ["Salad", "Veggie Stir-Fry", "Chic-Pea Alfredo", "Homemade Pizza", "Fondue", "Subway", "Dine Out Somewhere"],
            "Taco": ["Beef Tacos", "Chicken Tacos", "Shrimp Tacos", "Beef Nachos", "Chicken Nachos", "Steak Nachos", "Beef Quesdilla", "Chicken Quesdilla", "Steak Quesdilla", "Burrito Bowl", "Taco in a Bag"]
        },
        "sides": ["Rice", "Broccoli", "Side Salad", "Corn", "Small Red Potatoes", "Asparagus", "Green Beans", "Zucchini", "Carrots"],
        "ingredients": {},
        "shopping_status": {} 
    }

def load_user_data(username):
    user_file = os.path.join(PROFILE_DIR, f"{username}.json")
    try:
        with open(user_file, 'r') as f:
            data = json.load(f)
            # Ensure consistency (in case we add new features later)
            defaults = get_default_data()
            for key in defaults:
                if key not in data:
                    data[key] = defaults[key]
            return data
    except FileNotFoundError:
        # Fallback if file missing (shouldn't happen if created correctly)
        return get_default_data()

def save_user_data(username, data):
    user_file = os.path.join(PROFILE_DIR, f"{username}.json")
    with open(user_file, 'w') as f:
        json.dump(data, f, indent=4)

# --- LOGIC HELPERS ---

def get_days_remaining_in_month():
    today = datetime.date.today()
    next_month = today.replace(day=28) + datetime.timedelta(days=4)
    last_day = next_month - datetime.timedelta(days=next_month.day)
    
    days_left = []
    current = today
    while current <= last_day:
        days_left.append(current)
        current += timedelta(days=1)
    return days_left

def get_special_side_logic(dish_name, category):
    fixed_sides = {
        "Chicken Noodle Soup": "Garlic Bread",
        "Chicken Tenders": "Tater Tots",
        "Burgers": "Fries",
        "Beef Sliders": "Fries",
        "Smash Burgers": "Tater Tots",
        "Meatballs": "Pasta",
        "Fondue": "Ham, Broccoli, Green Apples, and Mountain Bread",
        "Taco in a Bag": "Chips"
    }
    if dish_name in fixed_sides: return fixed_sides[dish_name]

    no_side_exact = [
        "Homemade Pizza", "Subway", "Adobo", "Arroz Con Pollo", 
        "Korean Beef Rice Bowl", "Publix Deli", "Omelets", 
        "Egg Salad Sandwich", "Mac and Cheese", "Salad"
    ]
    if dish_name in no_side_exact: return "No Side"

    if category == "Taco": return "No Side"
    if "Stir-Fry" in dish_name: return "No Side"

    return None

def is_category_allowed(category, date, data, current_plan, week_category_counts):
    week_num = date.isocalendar()[1]
    if week_category_counts.get((week_num, category), 0) >= 2:
        return False
    history_limit = date - timedelta(days=3)
    all_records = data['history'] + current_plan
    for record in all_records:
        r_date = datetime.datetime.strptime(record['date'], "%Y-%m-%d").date()
        if r_date >= history_limit and r_date < date:
            if record['category'] == category:
                return False
    return True

def is_meat_allowed(meat, date, data, current_plan):
    history_limit = date - timedelta(days=21)
    all_records = data['history'] + current_plan
    for record in all_records:
        r_date = datetime.datetime.strptime(record['date'], "%Y-%m-%d").date()
        if r_date >= history_limit and r_date < date:
            if record['meat'] == meat:
                return False
    return True

def is_side_allowed(side, date, data, current_plan):
    if side == "No Side": return True
    history_limit = date - timedelta(days=5)
    all_records = data['history'] + current_plan
    for record in all_records:
        r_date = datetime.datetime.strptime(record['date'], "%Y-%m-%d").date()
        if r_date >= history_limit and r_date < date:
            if record['side'] == side:
                return False
    return True

def generate_schedule(data, username):
    days = get_days_remaining_in_month()
    new_plan = []
    week_category_counts = {} 
    
    data['shopping_status'] = {}

    for day in days:
        week_num = day.isocalendar()[1]
        
        # 1. Category
        if day.weekday() == 1: 
            category = "Taco"
        else:
            all_cats = [c for c in data['categories'].keys() if c != "Taco"]
            valid_cats = []
            for cat in all_cats:
                if is_category_allowed(cat, day, data, new_plan, week_category_counts):
                    valid_cats.append(cat)
            
            if not valid_cats:
                valid_cats = [c for c in all_cats if week_category_counts.get((week_num, c), 0) < 2]
            if not valid_cats:
                valid_cats = all_cats

            category = random.choice(valid_cats)

        # 2. Meat
        meat_options = data['categories'][category]
        valid_meats = []
        for m in meat_options:
            if is_meat_allowed(m, day, data, new_plan):
                valid_meats.append(m)
        
        if not valid_meats:
            chosen_meat = random.choice(meat_options)
        else:
            chosen_meat = random.choice(valid_meats)

        # 3. Side
        special_side = get_special_side_logic(chosen_meat, category)
        if special_side:
            chosen_side = special_side
        else:
            side_options = data['sides']
            valid_sides = []
            for s in side_options:
                if is_side_allowed(s, day, data, new_plan):
                    valid_sides.append(s)
            if not valid_sides:
                chosen_side = random.choice(side_options)
            else:
                chosen_side = random.choice(valid_sides)

        week_category_counts[(week_num, category)] = week_category_counts.get((week_num, category), 0) + 1
        
        new_plan.append({
            "date": day.strftime("%Y-%m-%d"),
            "day_name": day.strftime("%A"),
            "category": category,
            "meat": chosen_meat,
            "side": chosen_side
        })

    data['current_month_plan'] = new_plan
    save_user_data(username, data)
    return new_plan

def calculate_grocery_list(data):
    grocery_list = []
    missing_ing_dishes = []
    
    if not data['current_month_plan']:
        return [], []

    for meal in data['current_month_plan']:
        date = meal['date']
        # Meat Ingredients
        if meal['meat'] in data['ingredients']:
            for ing in data['ingredients'][meal['meat']]:
                grocery_list.append({
                    "name": ing, "dish": meal['meat'], "key": f"{ing}_{meal['meat']}_{date}" 
                })
        else:
            missing_ing_dishes.append(meal['meat'])
            
        # Side Ingredients
        if meal['side'] != "No Side":
            if meal['side'] in data['ingredients']:
                for ing in data['ingredients'][meal['side']]:
                    grocery_list.append({
                        "name": ing, "dish": meal['side'], "key": f"{ing}_{meal['side']}_{date}"
                    })
    
    grocery_list.sort(key=lambda x: x['name'])
    return grocery_list, missing_ing_dishes


# --- MAIN APP LOGIC ---

def main_app(username):
    # Sidebar
    st.sidebar.title(f"👤 {username}")
    if st.sidebar.button("Logout"):
        st.session_state.current_user = None
        st.rerun()

    data = load_user_data(username)

    menu = st.radio("Menu", ["Generate", "This Month", "Edit Meals", "Shopping List", "Send Out List"], horizontal=True)

    if menu == "Generate":
        st.header("Generate Schedule")
        st.write(f"Generate meals for the rest of {datetime.date.today().strftime('%B')}.")
        
        if 'confirm_override' not in st.session_state:
            st.session_state.confirm_override = False

        if st.button("Generate New List", type="primary"):
            if len(data['current_month_plan']) > 0:
                st.session_state.confirm_override = True
            else:
                with st.spinner("Cooking up a schedule..."):
                    plan = generate_schedule(data, username)
                st.success("Menu Generated!")
                st.dataframe(pd.DataFrame(plan)[['day_name', 'date', 'meat', 'side']])

        if st.session_state.confirm_override:
            st.warning("A list has already been generated for this month. Generating a new list will override the previous list. This can not be undone. Do you wish to continue and override?")
            col1, col2 = st.columns(2)
            
            if col1.button("Yes"):
                with st.spinner("Overriding..."):
                    plan = generate_schedule(data, username)
                st.session_state.confirm_override = False 
                st.success("New Menu Generated!")
                st.dataframe(pd.DataFrame(plan)[['day_name', 'date', 'meat', 'side']])
                
            if col2.button("No"):
                st.session_state.confirm_override = False 
                st.rerun() 

    elif menu == "This Month":
        st.header("This Month's Schedule")
        if not data['current_month_plan']:
            st.info("No plan generated yet.")
        else:
            df = pd.DataFrame(data['current_month_plan'])
            st.table(df[['day_name', 'date', 'meat', 'side']])

    elif menu == "Edit Meals":
        st.header("Database Manager")
        tab1, tab2, tab3 = st.tabs(["1. Manage Categories", "2. Manage Sides", "3. Manage Ingredients"])
        
        with tab1:
            cat_to_edit = st.selectbox("Select Category", list(data['categories'].keys()))
            current_items = ", ".join(data['categories'][cat_to_edit])
            new_items_str = st.text_area(f"Dishes for {cat_to_edit} (comma separated)", current_items)
            if st.button("Save Category Items"):
                new_list = [x.strip() for x in new_items_str.split(",")]
                data['categories'][cat_to_edit] = new_list
                save_user_data(username, data)
                st.success(f"Saved {cat_to_edit}!")

        with tab2:
            current_sides = ", ".join(data['sides'])
            new_sides_str = st.text_area("Sides (comma separated)", current_sides)
            if st.button("Save Sides"):
                new_list = [x.strip() for x in new_sides_str.split(",")]
                data['sides'] = new_list
                save_user_data(username, data)
                st.success("Sides Updated!")
                
        with tab3:
            all_dishes = []
            for cat in data['categories']:
                all_dishes.extend(data['categories'][cat])
            all_dishes.extend(data['sides'])
            all_dishes = sorted(list(set(all_dishes))) 
            
            selected_dish = st.selectbox("Select Dish to Edit Ingredients", all_dishes)
            existing_ing = ", ".join(data['ingredients'].get(selected_dish, []))
            new_ing_str = st.text_area(f"Ingredients needed for {selected_dish}", existing_ing)
            
            if st.button(f"Save Ingredients for {selected_dish}"):
                if new_ing_str.strip():
                    ing_list = [x.strip() for x in new_ing_str.split(",") if x.strip()]
                    data['ingredients'][selected_dish] = ing_list
                else:
                    if selected_dish in data['ingredients']:
                        del data['ingredients'][selected_dish]
                save_user_data(username, data)
                st.success("Ingredients Saved!")

    elif menu == "Shopping List":
        st.header("Shopping Checklist")
        if not data['current_month_plan']:
            st.warning("Please Generate a schedule first.")
        else:
            grocery_list, _ = calculate_grocery_list(data)
            if not grocery_list:
                st.info("No ingredients found.")
            else:
                st.write("Check off items as you shop:")
                def toggle_item_state(item_key):
                    data['shopping_status'][item_key] = not data['shopping_status'].get(item_key, False)
                    save_user_data(username, data)

                for item in grocery_list:
                    unique_key = item['key']
                    is_checked = data['shopping_status'].get(unique_key, False)
                    if is_checked:
                        label = f"~~{item['name']} ({item['dish']})~~"
                    else:
                        label = f"{item['name']} $\quad \\textcolor{{red}}{{\\small ({item['dish']})}}$"
                    st.checkbox(label, value=is_checked, key=unique_key, on_change=toggle_item_state, args=(unique_key,))

    elif menu == "Send Out List":
        st.header("Grocery List Export")
        if not data['current_month_plan']:
            st.warning("Please Generate a schedule first.")
        else:
            unique_grocery_list, missing_ing_dishes = calculate_grocery_list(data)
            if missing_ing_dishes:
                unique_missing = list(set(missing_ing_dishes))
                st.warning(f"⚠️ Missing ingredients for: {', '.join(unique_missing)}")
            
            msg_header = f"Grocery List for {datetime.date.today().strftime('%B')}:\n"
            list_lines = []
            for item in unique_grocery_list:
                list_lines.append(f"- {item['name']} ({item['dish']})")
            final_msg = msg_header + "\n".join(list_lines)
            
            st.text_area("Preview:", final_msg, height=300)
            encoded_msg = urllib.parse.quote(final_msg)
            st.markdown(f'''<a href="sms:&body={encoded_msg}"><button style="background-color:#4CAF50;color: white;padding: 10px 24px;border: none;border-radius: 4px;cursor: pointer;width: 100%;">📱 Send Grocery List as Text</button></a>''', unsafe_allow_html=True)

# --- LOGIN SCREEN ---

st.set_page_config(page_title="Dinner Planner", page_icon="🍽️")

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

if st.session_state.current_user is None:
    st.title("🍽️ Dinner Planner Login")
    
    tab1, tab2 = st.tabs(["Login", "Create Profile"])
    
    with tab1:
        st.subheader("Login")
        l_user = st.text_input("Username", key="l_user")
        l_pass = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login"):
            if authenticate(l_user, l_pass):
                st.session_state.current_user = l_user
                st.success(f"Welcome back, {l_user}!")
                st.rerun()
            else:
                st.error("Invalid Username or Password. If you don't have a profile, please check the 'Create Profile' tab.")

    with tab2:
        st.subheader("Create New Profile")
        c_user = st.text_input("Choose Username", key="c_user")
        c_pass = st.text_input("Choose Password", type="password", key="c_pass")
        if st.button("Create Profile"):
            if not c_user or not c_pass:
                st.warning("Please fill out both fields.")
            else:
                success, msg = create_user(c_user, c_pass)
                if success:
                    st.success("Profile created! Please switch to the Login tab to sign in.")
                else:
                    st.error(msg)
else:
    # Run the main app function, passing the logged-in user
    main_app(st.session_state.current_user)