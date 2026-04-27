import os

html_path = '/Users/akobir/Desktop/TASK-IN/Task_in/templates/landing.html'
with open(html_path, 'r') as f:
    content = f.read()

# Replace physical escaped raw backward slashes to standard JS compatible strings
content = content.replace(r'\"', '"')

with open(html_path, 'w') as f:
    f.write(content)

print('Successfully cleaned backward slashes breaking Django Syntax tags.')
