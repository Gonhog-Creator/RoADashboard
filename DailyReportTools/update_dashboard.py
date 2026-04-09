import re

# Read the dashboard file
with open('dashboard.py', 'r') as f:
    content = f.read()

# Update imports
content = content.replace('from Tabs.items import create_items_tab', 'from Tabs.items_enhanced import create_items_tab')

# Update tabs definition
old_tabs = 'tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["\ud83d\udcca Overview", "\ud83d\udc65 Player Count", "\ud83d\udcc8 Resources", "\u2694\ufe0f Power", "\u26a1 Speedups", "\ud83d\udce6 Items"])'
new_tabs = 'tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(["\ud83d\udcca Overview", "\ud83d\udc65 Player Count", "\ud83d\udcc8 Resources", "\u2694\ufe0f Power", "\u26a1 Speedups", "\ud83d\udce6 Items", "\u2694\ud83d\udc65 Troops", "\ud83c\udff0 Buildings", "\ud83c\udfa8 Skins", "\ud83d\udcdc Quests & Research"])'
content = content.replace(old_tabs, new_tabs)

# Add new tab content after tab6
old_content = '''    with tab6:
        create_items_tab(filtered_df)'''
new_content = '''    with tab6:
        create_items_tab(filtered_df)
    
    with tab7:
        create_troops_tab(filtered_df)
    
    with tab8:
        create_buildings_tab(filtered_df)
    
    with tab9:
        create_skins_tab(filtered_df)
    
    with tab10:
        create_quests_research_tab(filtered_df)'''

content = content.replace(old_content, new_content)

# Write back to file
with open('dashboard.py', 'w') as f:
    f.write(content)

print("Dashboard updated successfully!")
