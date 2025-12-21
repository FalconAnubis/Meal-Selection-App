import streamlit as st
import datetime
import random
import json
import pandas as pd
import urllib.parse
from datetime import timedelta

# --- CONFIGURATION & DATA STORAGE ---
DATA_FILE = 'dinner_data.json'

def load_data():
    default_data = {
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
        "ingredients": {} 
    }
    
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Ensure new keys exist if loading old file version
            if "ingredients" not in data:
                data["ingredients"] = {}
            return data
    except FileNotFoundError:
        return default_data

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- LOGIC HELPERS ---

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

def get_special_side_logic(dish_name, category):
    """
    Determines if a dish has a fixed side or no side.
    Returns: The Side Name (str) or None (if it should be random).
    """
    
    # 1. FIXED SIDES (These override everything else)
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
    
    if dish_name in fixed_sides:
        return fixed_sides[dish_name]

    # 2. NO SIDE LIST (Exact Matches)
    no_side_exact = [
        "Homemade Pizza", "Subway", "Adobo", "Arroz Con Pollo", 
        "Korean Beef Rice Bowl", "Publix Deli", "Omelets", 
        "Egg Salad Sandwich", "Mac and Cheese", "Salad"
    ]
    
    if dish_name in no_side_exact:
        return "No Side"

    # 3. NO SIDE CATEGORY RULES
    # Rule: All Tacos get No Side (Unless caught by Fixed Side above, like Taco in a Bag)
    if category == "Taco":
        return "No Side"
        
    # Rule: Any Stir-Fry gets No Side
    if "Stir-Fry" in dish_name:
        return "No Side"

    # If neither fixed nor forbidden, return None (implies Random)
    return None

def check_constraints(date, category, item, side, data, week_category_counts):
    # 1. Category max 2 times a week
    week_num = date.isocalendar()[1]
    if week_category_counts.get((week_num, category), 0) >= 2:
        return False

    # 2. Setup History Lookbacks
    history_limit_item = date - timedelta(weeks=3)
    history_limit_side = date - timedelta(days=5) 

    all_records = data['history'] + data['current_month_plan']

    for record in all_records:
        record_date = datetime.datetime.strptime(record['date'], "%Y-%m-%d").date()
        
        # Rule: No repeat Meat for 3 weeks
        if record['meat'] == item and record_date >= history_limit_item and record_date < date:
            return False
            
        # Rule: Side Cooldown (5 Days) - ONLY applies to random sides
        # If side is "No Side", we don't care about cooldowns
        if side != "No Side":
            if record['side'] == side and record_date >= history_limit_side and record_date < date:
                return False
            
    return True

def generate_schedule(data):
    days = get_days_remaining_in_month()
    new_plan = []
    week_category_counts = {} 
    
    for day in days:
        week_num = day.isocalendar()[1]
        
        # --- TACO TUESDAY ---
        if day.weekday() == 1: 
            category = "Taco"
            taco_options = data['categories']['Taco']
            # Rotate meat logic could go here, for now random
            chosen_meat = random.choice(taco_options)
        
        # --- STANDARD DAY ---
        else:
            # Pick Category
            valid_cats = [c for c in data['categories'].keys() if c != "Taco"]
            random.shuffle(valid_cats)
            category = None
            for cat in valid_cats:
                if week_category_counts.get((week_num, cat), 0) < 2:
                    category = cat
                    break
            if not category: category = random.choice(valid_cats)

            meat_options = data['categories'][category]
            chosen_meat = random.choice(meat_options)

        # --- DETERMINE SIDE ---
        # 1. Check if this meat has a forced/special side
        special_side = get_special_side_logic(chosen_meat, category)
        
        if special_side:
            chosen_side = special_side
            # We skip constraint checking for Fixed Sides because they are mandatory
        else:
            # 2. Random Side Selection
            side_options = data['sides']
            chosen_side = random.choice(side_options)
            
            # Try 50 times to find a valid combo (Cooldowns applied here)
            # We re-roll both meat and side to find a combo that fits constraints
            for _ in range(50):
                if check_constraints(day, category, chosen_meat, chosen_side, data, week_category_counts):
                    break
                # If failed, re-roll
                chosen_meat = random.choice(data['categories'][category])
                
                # Check if the NEW meat has a special side
                new_special = get_special_side_logic(chosen_meat, category)
                if new_special:
                    chosen_side = new_special
                    # If special side found, we accept this meat (assuming meat history is ok)
                    break 
                else:
                    chosen_side = random.choice(side_options)

        week_category_counts[(week_num, category)] = week_category_counts.get((week_num, category), 0) + 1
        
        new_plan.append({
            "date": day.strftime("%Y-%m-%d"),
            "day_name": day.strftime("%A"),
            "category": category,
            "meat": chosen_meat,
            "side": chosen_side
        })

    data['current_month_plan'] = new_plan
    save_data(data)
    return new_plan

# --- UI LAYOUT ---
st.set_page_config(page_title="Dinner Planner", page_icon="🍽️")
st.title("🍽️ Dinner & Grocery App")

data = load_data()

# Navigation
menu = st.radio("Menu", ["Generate", "This Month", "Edit Meals", "Send Out List"], horizontal=True)

if menu == "Generate":
    st.header("Generate Schedule")
    st.write(f"Generate meals for the rest of {datetime.date.today().strftime('%B')}.")
    
    if st.button("Generate New List", type="primary"):
        with st.spinner("Calculating logic..."):
            plan = generate_schedule(data)
        st.success("Menu Generated!")
        st.dataframe(pd.DataFrame(plan)[['day_name', 'date', 'meat', 'side']])

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
            save_data(data)
            st.success(f"Saved {cat_to_edit}!")

    with tab2:
        current_sides = ", ".join(data['sides'])
        new_sides_str = st.text_area("Sides (comma separated)", current_sides)
        if st.button("Save Sides"):
            new_list = [x.strip() for x in new_sides_str.split(",")]
            data['sides'] = new_list
            save_data(data)
            st.success("Sides Updated!")
            
    with tab3:
        st.info("Assign grocery ingredients to specific dishes (Meats or Sides).")
        
        # Compile a master list of all known dishes and sides
        all_dishes = []
        for cat in data['categories']:
            all_dishes.extend(data['categories'][cat])
        all_dishes.extend(data['sides'])
        all_dishes = sorted(list(set(all_dishes))) # Unique & Sorted
        
        selected_dish = st.selectbox("Select Dish to Edit Ingredients", all_dishes)
        
        # Get existing ingredients
        existing_ing = ", ".join(data['ingredients'].get(selected_dish, []))
        
        new_ing_str = st.text_area(f"Ingredients needed for {selected_dish}", existing_ing, help="Separate by comma (e.g. Ground Beef, Cheese, Shells)")
        
        if st.button(f"Save Ingredients for {selected_dish}"):
            if new_ing_str.strip():
                ing_list = [x.strip() for x in new_ing_str.split(",") if x.strip()]
                data['ingredients'][selected_dish] = ing_list
            else:
                if selected_dish in data['ingredients']:
                    del data['ingredients'][selected_dish]
            save_data(data)
            st.success("Ingredients Saved!")

elif menu == "Send Out List":
    st.header("Grocery List Export")
    
    if not data['current_month_plan']:
        st.warning("Please Generate a schedule first.")
    else:
        st.write("Aggregating ingredients based on the current schedule...")
        
        grocery_list = []
        missing_ing_dishes = []
        
        for meal in data['current_month_plan']:
            # 1. Get meat ingredients
            if meal['meat'] in data['ingredients']:
                grocery_list.extend(data['ingredients'][meal['meat']])
            else:
                missing_ing_dishes.append(meal['meat'])
                
            # 2. Get side ingredients (Only if side exists and has ingredients)
            if meal['side'] != "No Side":
                if meal['side'] in data['ingredients']:
                    grocery_list.extend(data['ingredients'][meal['side']])
                # Note: We intentionally removed the "else missing_ing_dishes" for sides here
        
        # Deduplicate list and sort
        unique_grocery_list = sorted(list(set(grocery_list)))
        
        # Display warnings for missing MEAT data only
        if missing_ing_dishes:
            unique_missing = list(set(missing_ing_dishes))
            st.warning(f"⚠️ The following Main Dishes have no ingredients defined: {', '.join(unique_missing)}")
            
        # Format Message
        msg_header = f"Grocery List for {datetime.date.today().strftime('%B')}:\n"
        msg_body = "\n".join([f"- {item}" for item in unique_grocery_list])
        final_msg = msg_header + msg_body
        
        st.text_area("Preview:", final_msg, height=300)
        
        # SMS Button
        encoded_msg = urllib.parse.quote(final_msg)
        st.markdown(f'''<a href="sms:&body={encoded_msg}"><button style="
            background-color:#4CAF50;
            color: white;
            padding: 10px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            width: 100%;">
            📱 Send Grocery List as Text
            </button></a>''', unsafe_allow_html=True)
