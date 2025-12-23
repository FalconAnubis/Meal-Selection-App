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

if not os.path.exists(PROFILE_DIR):
    os.makedirs(PROFILE_DIR)

# --- SECURITY & AUTH FUNCTIONS ---

def hash_pin(pin):
    """Hashes a numeric PIN."""
    return hashlib.sha256(str.encode(pin)).hexdigest()

def load_user_db():
    try:
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_db(db):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

def authenticate_pin(username, pin_input):
    db = load_user_db()
    if username in db:
        # Check against the stored PIN hash
        stored_hash = db[username]['pin_hash']
        if stored_hash == hash_pin(pin_input):
            return True
    return False

def create_user(username, pin):
    db = load_user_db()
    if username in db:
        return False, "User already exists."
    
    # Assign a random avatar emoji for the profile button
    avatars = ["👨‍🍳", "👩‍🍳", "🦁", "🐯", "🤖", "👽", "🥑", "🌮"]
    
    db[username] = {
        "pin_hash": hash_pin(pin),
        "avatar": random.choice(avatars)
    }
    save_user_db(db)
    
    default_data = get_default_data()
    user_file = os.path.join(PROFILE_DIR, f"{username}.json")
    with open(user_file, 'w') as f:
        json.dump(default_data, f, indent=4)
        
    return True, "User created successfully."

def update_user_identity(old_name, new_name, new_avatar):
    """Handles renaming a user and updating their avatar safely."""
    db = load_user_db()
    
    # 1. Validation: If name is changing, ensure new name isn't taken
    if new_name != old_name and new_name in db:
        return False, "Username already taken."
    
    # 2. Prepare Data
    if old_name not in db:
        return False, "User not found."
        
    user_data = db[old_name]
    user_data['avatar'] = new_avatar
    
    # 3. Handle Name Change (Rename Keys and Files)
    if new_name != old_name:
        # Create new key, delete old key
        db[new_name] = user_data
        del db[old_name]
        
        # Rename the physical .json file
        old_file = os.path.join(PROFILE_DIR, f"{old_name}.json")
        new_file = os.path.join(PROFILE_DIR, f"{new_name}.json")
        if os.path.exists(old_file):
            os.rename(old_file, new_file)
    else:
        # Just update the avatar in the existing key
        db[old_name] = user_data
            
    save_user_db(db)
    return True, "Profile Updated!"

# --- DATA MANAGEMENT ---

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
            defaults = get_default_data()
            for key in defaults:
                if key not in data:
                    data[key] = defaults[key]
            return data
    except FileNotFoundError:
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
        "Chicken Noodle Soup": "Garlic Bread", "Chicken Tenders": "Tater Tots",
        "Burgers": "Fries", "Beef Sliders": "Fries", "Smash Burgers": "Tater Tots",
        "Meatballs": "Pasta", "Fondue": "Ham, Broccoli, Green Apples, and Mountain Bread",
        "Taco in a Bag": "Chips"
    }
    if dish_name in fixed_sides: return fixed_sides[dish_name]
    no_side_exact = ["Homemade Pizza", "Subway", "Adobo", "Arroz Con Pollo", "Korean Beef Rice Bowl", "Publix Deli", "Omelets", "Egg Salad Sandwich", "Mac and Cheese", "Salad"]
    if dish_name in no_side_exact: return "No Side"
    if category == "Taco" or "Stir-Fry" in dish_name: return "No Side"
    return None

def is_category_allowed(category, date, data, current_plan, week_category_counts):
    week_num = date.isocalendar()[1]
    if week_category_counts.get((week_num, category), 0) >= 2: return False
    history_limit = date - timedelta(days=3)
    all_records = data['history'] + current_plan
    for record in all_records:
        r_date = datetime.datetime.strptime(record['date'], "%Y-%m-%d").date()
        if r_date >= history_limit and r_date < date:
            if record['category'] == category: return False
    return True

def is_meat_allowed(meat, date, data, current_plan):
    history_limit = date - timedelta(days=21)
    all_records = data['history'] + current_plan
    for record in all_records:
        r_date = datetime.datetime.strptime(record['date'], "%Y-%m-%d").date()
        if r_date >= history_limit and r_date < date:
            if record['meat'] == meat: return False
    return True

def is_side_allowed(side, date, data, current_plan):
    if side == "No Side": return True
    history_limit = date - timedelta(days=5)
    all_records = data['history'] + current_plan
    for record in all_records:
        r_date = datetime.datetime.strptime(record['date'], "%Y-%m-%d").date()
        if r_date >= history_limit and r_date < date:
            if record['side'] == side: return False
    return True

def generate_schedule(data, username):
    days = get_days_remaining_in_month()
    new_plan = []
    week_category_counts = {} 
    data['shopping_status'] = {}

    for day in days:
        week_num = day.isocalendar()[1]
        
        # 1. Category
        if day.weekday() == 1: category = "Taco"
        else:
            all_cats = [c for c in data['categories'].keys() if c != "Taco"]
            valid_cats = [c for c in all_cats if is_category_allowed(c, day, data, new_plan, week_category_counts)]
            if not valid_cats: valid_cats = [c for c in all_cats if week_category_counts.get((week_num, c), 0) < 2]
            if not valid_cats: valid_cats = all_cats
            category = random.choice(valid_cats)

        # 2. Meat
        meat_options = data['categories'][category]
        valid_meats = [m for m in meat_options if is_meat_allowed(m, day, data, new_plan)]
        chosen_meat = random.choice(valid_meats) if valid_meats else random.choice(meat_options)

        # 3. Side
        special_side = get_special_side_logic(chosen_meat, category)
        if special_side:
            chosen_side = special_side
        else:
            side_options = data['sides']
            valid_sides = [s for s in side_options if is_side_allowed(s, day, data, new_plan)]
            chosen_side = random.choice(valid_sides) if valid_sides else random.choice(side_options)

        week_category_counts[(week_num, category)] = week_category_counts.get((week_num, category), 0) + 1
        new_plan.append({"date": day.strftime("%Y-%m-%d"), "day_name": day.strftime("%A"), "category": category, "meat": chosen_meat, "side": chosen_side})

    data['current_month_plan'] = new_plan
    save_user_data(username, data)
    return new_plan

def calculate_grocery_list(data):
    grocery_list = []
    missing_ing_dishes = []
    if not data['current_month_plan']: return [], []

    today = datetime.date.today()
    cutoff_date = today + datetime.timedelta(days=7)

    for meal in data['current_month_plan']:
        meal_date_obj = datetime.datetime.strptime(meal['date'], "%Y-%m-%d").date()
        if meal_date_obj < today: continue 
        if meal_date_obj > cutoff_date: continue

        date_str = meal['date']
        
        # Meat
        if meal['meat'] in data['ingredients']:
            for ing in data['ingredients'][meal['meat']]:
                grocery_list.append({"name": ing, "dish": meal['meat'], "key": f"{ing}_{meal['meat']}_{date_str}"})
        else:
            missing_ing_dishes.append(meal['meat'])
            
        # Side
        if meal['side'] != "No Side":
            if meal['side'] in data['ingredients']:
                for ing in data['ingredients'][meal['side']]:
                    grocery_list.append({"name": ing, "dish": meal['side'], "key": f"{ing}_{meal['side']}_{date_str}"})
    
    grocery_list.sort(key=lambda x: x['name'])
    return grocery_list, missing_ing_dishes


# --- VIEWS (PROFILE vs PLANNER) ---

def render_profile_page(username, data):
    # --- SECTION 1: IDENTITY (Name & Avatar) ---
    st.header(f"⚙️ Profile Settings")
    
    # Load current user settings to pre-fill the form
    users_db = load_user_db()
    current_avatar = users_db[username].get('avatar', '👤') if username in users_db else '👤'
    
    with st.container(border=True):
        st.subheader("My Identity")
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # Avatar Selection
            avatars = ["👨‍🍳", "👩‍🍳", "🦁", "🐯", "🤖", "👽", "🥑", "🌮", "🥓", "🦄"]
            # find index safely
            default_index = avatars.index(current_avatar) if current_avatar in avatars else 0
            new_avatar = st.selectbox("Avatar", avatars, index=default_index)
        
        with col2:
            # Name Edit
            new_name = st.text_input("Display Name", value=username)
            
        if st.button("💾 Save Profile Changes"):
            if new_name.strip():
                success, msg = update_user_identity(username, new_name, new_avatar)
                if success:
                    st.success(msg)
                    # Update session state if name changed so the app doesn't crash
                    st.session_state.current_user = new_name
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Name cannot be empty.")

    st.divider()

    # --- SECTION 2: MEAL DATABASE ---
    st.subheader("My Kitchen Database")
    st.info("Edit your personal collection of foods here.")

    tab1, tab2, tab3 = st.tabs(["1. Manage Categories", "2. Manage Sides", "3. Manage Ingredients"])
    
    with tab1:
        cat_to_edit = st.selectbox("Select Category", list(data['categories'].keys()))
        current_items = ", ".join(data['categories'][cat_to_edit])
        new_items_str = st.text_area(f"Dishes for {cat_to_edit} (comma separated)", current_items, height=150)
        if st.button("Save Category Items"):
            new_list = [x.strip() for x in new_items_str.split(",")]
            data['categories'][cat_to_edit] = new_list
            save_user_data(username, data)
            st.success(f"Saved {cat_to_edit}!")

    with tab2:
        current_sides = ", ".join(data['sides'])
        new_sides_str = st.text_area("Sides (comma separated)", current_sides, height=150)
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
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(f"Save Ingredients"):
                if new_ing_str.strip():
                    ing_list = [x.strip() for x in new_ing_str.split(",") if x.strip()]
                    data['ingredients'][selected_dish] = ing_list
                else:
                    if selected_dish in data['ingredients']:
                        del data['ingredients'][selected_dish]
                save_user_data(username, data)
                st.success("Ingredients Saved!")
        
        with col_b:
             if st.button("← Back to Planner", use_container_width=True):
                st.session_state.app_mode = "Planner"
                st.rerun()

def render_planner_page(username, data):
    menu = st.radio("Menu", ["Generate", "This Month", "Shopping List"], horizontal=True)

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
            st.warning("Warning: Overriding existing plan. Continue?")
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

    elif menu == "Shopping List":
        st.header("Shopping Checklist (Next 7 Days)")
        if not data['current_month_plan']:
            st.warning("Please Generate a schedule first.")
        else:
            grocery_list, missing_ing_dishes = calculate_grocery_list(data)
            
            if missing_ing_dishes:
                unique_missing = list(set(missing_ing_dishes))
                st.warning(f"⚠️ Missing ingredients for: {', '.join(unique_missing)}")
                
            if not grocery_list:
                st.info("No meals found for the next 7 days (or no ingredients defined).")
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
            
            st.divider()
            with st.expander("📤 Export List via SMS"):
                msg_header = f"Grocery List (Next 7 Days):\n"
                list_lines = []
                for item in grocery_list:
                    list_lines.append(f"- {item['name']} ({item['dish']})")
                final_msg = msg_header + "\n".join(list_lines)
                
                st.text_area("Preview Message:", final_msg, height=200)
                encoded_msg = urllib.parse.quote(final_msg)
                st.markdown(f'''<a href="sms:&body={encoded_msg}"><button style="background-color:#4CAF50;color: white;padding: 10px 24px;border: none;border-radius: 4px;cursor: pointer;width: 100%;">📱 Open in Messages</button></a>''', unsafe_allow_html=True)

# --- MAIN CONTROLLER ---

st.set_page_config(page_title="Dinner Planner", page_icon="🍽️")

# Session State Initialization
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'app_mode' not in st.session_state:
    st.session_state.app_mode = "Planner"
if 'selected_user_for_login' not in st.session_state:
    st.session_state.selected_user_for_login = None

# --- AUTHENTICATION FLOW ---

if st.session_state.current_user is None:
    st.title("🍽️ Who is cooking?")
    
    users_db = load_user_db()
    
    # 1. IF NO USER SELECTED YET: SHOW PROFILE GRID
    if st.session_state.selected_user_for_login is None:
        
        # Display existing users as buttons
        if users_db:
            # Create columns for a grid layout
            cols = st.columns(3)
            for i, (u_name, u_data) in enumerate(users_db.items()):
                # Use modulo to cycle through columns
                with cols[i % 3]:
                    # Large Button with Avatar and Name
                    avatar = u_data.get('avatar', '👤')
                    if st.button(f"{avatar}\n\n{u_name}", use_container_width=True, key=f"btn_{u_name}"):
                        st.session_state.selected_user_for_login = u_name
                        st.rerun()
        else:
            st.info("No profiles found. Create the first one below!")

        st.divider()
        
        # "Add User" Section (Always visible at bottom)
        with st.expander("➕ Add New Profile"):
            new_user = st.text_input("Name")
            new_pin = st.text_input("Create 4-Digit PIN", type="password", max_chars=4)
            if st.button("Create Profile"):
                if new_user and len(new_pin) == 4 and new_pin.isdigit():
                    success, msg = create_user(new_user, new_pin)
                    if success:
                        st.success(f"Created {new_user}! Select them above.")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter a name and a 4-digit numeric PIN.")

    # 2. IF USER SELECTED: SHOW PIN PAD
    else:
        target_user = st.session_state.selected_user_for_login
        user_avatar = users_db[target_user].get('avatar', '👤')
        
        st.markdown(f"<h2 style='text-align: center;'>{user_avatar} Hello, {target_user}</h2>", unsafe_allow_html=True)
        st.write("Enter your PIN to unlock your recipes.")
        
        # PIN Input
        pin_attempt = st.text_input("PIN", type="password", max_chars=4, key="login_pin")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔓 Unlock", type="primary", use_container_width=True):
                if authenticate_pin(target_user, pin_attempt):
                    st.session_state.current_user = target_user
                    st.session_state.selected_user_for_login = None # Clear selection
                    st.session_state.app_mode = "Planner"
                    st.success("Success!")
                    st.rerun()
                else:
                    st.error("Incorrect PIN")
        
        with col2:
            if st.button("⬅️ Switch User", use_container_width=True):
                st.session_state.selected_user_for_login = None
                st.rerun()

# --- MAIN APP FLOW ---

else:
    # User is Logged In
    username = st.session_state.current_user
    data = load_user_data(username)
    
    # Sidebar Navigation
    st.sidebar.title(f"Kitchen: {username}")
    
    if st.sidebar.button(f"👤 Edit Profile / Ingredients"):
        st.session_state.app_mode = "Profile"
        st.rerun()
        
    st.sidebar.divider()
    
    # LOGOUT becomes "Lock Profile"
    if st.sidebar.button("🔒 Lock Profile"):
        st.session_state.current_user = None
        st.session_state.app_mode = "Planner"
        st.rerun()

    # Render Active Page
    if st.session_state.app_mode == "Profile":
        render_profile_page(username, data)
    else:
        render_planner_page(username, data)