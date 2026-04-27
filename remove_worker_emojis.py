import os

files_to_check = [
    'templates/landing.html',
    'templates/landing_new.html',
    'static/js/landing.js',
    'static/js/landing_new.js'
]

emojis_to_remove = ['👨‍🔧', '👨\u200d⚡', '👩\u200d🧽', '👨\u200d❄️', '👨\u200d🎨']

for filepath in files_to_check:
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
            
        modified = False
        for emoji in emojis_to_remove:
            if f"icon: '{emoji}'" in content:
                content = content.replace(f"icon: '{emoji}'", "icon: ''")
                modified = True
                
        if modified:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"Removed emojis from {filepath}")
print("Finished.")
