                                               
# Group Project: CUSRR Website
### By: Yubin Moon, Lucas Lefevbre, Anya Brewer, Jack Reddy 
# Running it locally: 
- Open Terminal: 
    - cd to working directory 
    - git clone https://github.com/Jack-Reddy/CUSRR-Site.git
    - python3 app.py 

# Running it on Heroku/On the cloud: 
- https://cusrr-app-403f0d6a73c9.herokuapp.com/
    - **NEW** : Mobile Friendly to an extent!

# Features!
## _sidebar.html
- Given different role/authentication levels, different buttons/webpages can be accessed.
- If Attendee: 
    - Show Schedule and Dashboard
- If Presenter: 
    - Show Schedule, Dashboard, Profile Information
- If Abstract Grader:
    - Show Schedule, Dashboard, Abstract Grading Dashboard
- If Organizer: 
    - Show Schedule, Dashboard, Abstract Grading Dashboard, Attendees List, Presentations List, Grades Dashboard

## signup.html, or Sign Up
- Everything is done by Google Authentication, so there is no need to memorize usernames and passkeys
- Users write their first name, last name, and activity type when applicable

## profile.html, or Profile/Account Information
- After sign up, all user types can see their name, email, role, activity, and presentation, all if applicable
- If presentor, they can upload abstracts and presentations
- If a presentor has a partner and they are uploading materials for the two of them, partner's email should be written and will connect the two students in the database

## dashboard.html, or General Dashboard
- Top three selections show specific presentation types to be presented: Poster, Blitz, or Presentation
- Scroll down to see a full list of all presentation types to be presented

## schedule.html, or Schedule
- Select different days, and make blocks with time, date, location, and descriptions that could be changed

## abstract-grader.html, or Abstract Grader Dashboard
- Abstract graders are able to grade abstracts here, and completed grading is marked as complete
- Abstracts can be searched for, but Abstract Graders cannot see authors

## organizer-user-status.html, or Attendees List 
- Organizers can see a comprehensive list of students signed up with emails, activities, presentation IDs, roles, and their account status as complete or incomplete
- If incomplete, organizers can easily send mass emails to those selected as such 
- Attendees can be imported by .CSV, and they can also be searched for

## organizer-presentations-status.html, or Presentations Dashboard
- Organizers can see a comprehensive list of presentations with titles, subjects, presentation types, times scheduled, presentor(s) and can edit information whenever necessary
- Organizers can also download all presentations to present 
- Presentations can be searched for

## grades_dashboard.html, or Grades Dashboard
- Organizers can see a comprehensive list of scored for each presentation with titles, average presentation grade, average abstract grade, number of presentation grades, and number of abstract grades 
- Presentations can be searched for by title 


