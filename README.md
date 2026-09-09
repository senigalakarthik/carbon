# Personal Travel Carbon Intelligence

Track your travel, understand your carbon footprint, and make smaller, smarter changes.

Personal Travel Carbon Intelligence is a single-file Flask web application that helps users understand the environmental impact of their everyday travel.

The application analyzes logged journeys, estimates CO2 emissions, compares alternative transportation modes, identifies recurring travel patterns, and recommends the smallest realistic change with the biggest carbon benefit based on the user's own tolerance for extra travel time and cost.

It also includes an optional AI Travel Coach powered through OpenRouter.

## Features

### My Travel

* Log individual journeys
* Record date, origin, destination, purpose, transportation mode, distance, travel time, and cost
* View trip history
* Delete previously logged trips
* Automatically calculate CO2 emissions

### My Carbon

View your overall travel footprint with:

* Total CO2 emissions
* Average monthly CO2
* Highest-emission transportation mode
* Highest-emission travel purpose
* CO2 breakdown by transportation mode
* CO2 breakdown by trip purpose
* Highest-carbon individual journeys

Charts are rendered using Chart.js.

### My Patterns

The application detects recurring journeys based on origin, destination, and purpose.

For each recurring pattern it calculates:

* Trip frequency
* Dominant transportation mode
* Average distance
* Average travel time
* Average cost
* Total CO2 impact

This allows recommendations to focus on travel habits rather than isolated trips.

### Compare Options

Compare alternative transportation methods for the same journey.

The application evaluates:

* CO2 emissions
* Cost
* Travel time
* Additional time required
* Additional cost
* CO2 reduction percentage
* Money saved

Only realistic alternatives are considered.

### Set My Limits

Define your Acceptable Change Zone:

* Maximum extra travel time
* Maximum additional cost
* Minimum required CO2 reduction

The recommendation engine uses these limits when deciding which alternatives are realistic.

### Best Realistic Change

The application identifies the best transportation change based on your existing travel habits.

The recommendation prioritizes the biggest recurring CO2 reduction that still fits within your personal limits.

It also calculates estimated:

* Weekly CO2 savings
* Monthly CO2 savings
* Yearly CO2 savings
* Weekly, monthly, and yearly monetary savings

### What If

Experiment with different weekly transportation mixes.

Adjust the number of weekly trips using:

* Car
* Metro or Train
* Bus
* Bicycle
* Walking
* Carpool

The application estimates:

* Projected monthly CO2
* CO2 avoided
* Annual money savings
* Additional weekly travel time

### Track My Progress

Compare travel behavior before and after a selected change date.

The dashboard shows:

* CO2 avoided per month
* Money saved per month
* Car-type trip share
* Overall CO2 improvement

A before-and-after chart makes behavioral changes easy to understand.

### Smart Alerts

The application can detect changes in travel patterns and carbon emissions.

Alerts can provide:

* Detected changes
* Explanations
* Suggestions for improvement

The goal is to provide actionable feedback without encouraging drastic lifestyle changes.

### My Contribution

The application estimates the impact of choosing lower-carbon transportation.

It can calculate:

* CO2 avoided
* Approximate fuel saved
* Vehicle trips avoided
* Vehicle kilometres reduced
* Tree-equivalent annual absorption

These values are estimates and should not be interpreted as direct environmental measurements.

### AI Travel Coach

The built-in AI Travel Coach can answer questions about your travel behavior.

For example:

```text
What's my easiest win this month?
```

The AI receives relevant analytics such as:

* Total logged CO2
* Number of trips
* Acceptable Change Zone
* Current best recommendation
* Highest CO2-contributing transportation modes

The AI is designed around small and realistic changes rather than drastic lifestyle changes.

## Supported Transportation Modes

| Mode           | CO2 Factor | Cost per km | Average Speed |
| -------------- | ---------: | ----------: | ------------: |
| Car (Petrol)   |   192 g/km |     Rs 9.00 |       28 km/h |
| Car (Electric) |    53 g/km |     Rs 3.20 |       28 km/h |
| Motorbike      |   103 g/km |     Rs 2.80 |       32 km/h |
| Carpool        |    96 g/km |     Rs 4.50 |       28 km/h |
| Rideshare/Taxi |   150 g/km |    Rs 14.00 |       26 km/h |
| Bus            |    82 g/km |     Rs 1.50 |       18 km/h |
| Metro/Train    |    41 g/km |     Rs 2.00 |       34 km/h |
| Bicycle        |     0 g/km |        Rs 0 |       15 km/h |
| Walking        |     0 g/km |        Rs 0 |        5 km/h |

The values are configured as illustrative emission factors and cost assumptions within the application.

## How CO2 Is Calculated

For each trip:

```text
CO2 (kg) = Distance (km) x Emission Factor (g/km) / 1000
```

Travel cost:

```text
Cost = Distance (km) x Cost per km
```

Estimated travel time:

```text
Time = (Distance / Average Speed) x 60 + Overhead
```

The application also prevents unrealistic alternatives such as walking or cycling beyond their configured practical distance limits.

## Recommendation Logic

The recommendation engine works in several stages:

1. Identify recurring travel patterns.
2. Determine the dominant transportation mode for each pattern.
3. Calculate realistic alternative modes.
4. Compare CO2, time, and cost.
5. Apply the user's Acceptable Change Zone.
6. Calculate weekly, monthly, and yearly impact.
7. Select the option with the greatest recurring CO2 benefit.
8. Identify the minimum-change and maximum-impact option.

This makes the recommendation more personalized than simply suggesting the transportation method with the lowest emissions.

## Technology Stack

### Backend

* Python
* Flask
* Requests

### Frontend

* HTML5
* CSS3
* JavaScript
* Chart.js
* Google Fonts

### AI

* OpenRouter API
* User-selected language model

### Storage

The current version uses an in-memory data store.

Trip records are maintained in Python memory, so data will reset when the application restarts.

## Project Structure

The current project is implemented as a single Python file.

```text
personal-travel-carbon-intelligence/
|
|-- app.py
|-- README.md
```

The application contains:

```text
Configuration
    |
CO2, Cost and Time Calculations
    |
Trip Data
    |
Analytics
    |
Recommendation Engine
    |
AI Travel Coach
    |
Flask API Routes
    |
HTML, CSS and JavaScript Frontend
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/personal-travel-carbon-intelligence.git
cd personal-travel-carbon-intelligence
```

### 2. Install dependencies

```bash
pip install flask requests
```

### 3. Run the application

```bash
python app.py
```

### 4. Open the application

Open the following address in your browser:

```text
http://127.0.0.1:5000
```

## Setting Up the AI Travel Coach

The AI Travel Coach is optional.

It uses OpenRouter to send chat requests to the selected AI model.

### Step 1: Get an OpenRouter API Key

Create an API key from the OpenRouter website.

### Step 2: Open the AI Travel Coach

Use the chat section in the application.

### Step 3: Add Your API Key

Open the settings section and enter your OpenRouter API key.

The key is stored in the browser's local storage and sent with individual chat requests. The Flask server does not persist the key.

### Default Model

The default model is:

```text
openai/gpt-4o-mini
```

You can select another supported OpenRouter model through the chat settings.

Never commit your OpenRouter API key to GitHub or place it directly inside the source code.

## API Endpoints

| Endpoint              | Method   | Description                                  |
| --------------------- | -------- | -------------------------------------------- |
| `/`                   | GET      | Serves the web application                   |
| `/api/modes`          | GET      | Returns transportation modes and purposes    |
| `/api/trips`          | GET      | Returns logged trips                         |
| `/api/trips`          | POST     | Creates a new trip                           |
| `/api/trips/<id>`     | DELETE   | Deletes a trip                               |
| `/api/summary`        | GET      | Returns travel and carbon summary            |
| `/api/patterns`       | GET      | Returns recurring travel patterns            |
| `/api/limits`         | GET/POST | Reads or updates user limits                 |
| `/api/recommendation` | GET      | Returns personalized recommendations         |
| `/api/whatif`         | POST     | Calculates What If projections               |
| `/api/progress`       | GET      | Calculates before and after progress         |
| `/api/alerts`         | GET      | Returns travel and carbon alerts             |
| `/api/contribution`   | GET      | Returns estimated environmental contribution |
| `/api/chat`           | POST     | Sends a request to OpenRouter                |

## Demo Data

The application includes automatically generated demo travel data when it starts.

The demo data allows users to immediately explore:

* Travel history
* Carbon statistics
* Recurring travel patterns
* Transportation comparisons
* Recommendations
* What If scenarios
* Progress tracking
* Environmental contribution

## Limitations

### Data Persistence

Travel data is currently stored only in memory.

Restarting the Flask application resets the trip data.

### Emission Estimates

CO2 values are estimates based on configured emission factors rather than live vehicle, route, traffic, or electricity-grid data.

### Cost Estimates

Transportation costs are based on configured average cost-per-kilometre values and should not be interpreted as live fares or fuel prices.

### AI Availability

The AI Travel Coach requires:

* An OpenRouter API key
* Internet connectivity
* A valid OpenRouter model

The rest of the application can still be used without the AI functionality.

## Privacy

The application is designed so that an OpenRouter API key is not hardcoded or permanently stored on the Flask server.

The browser stores the user's key locally and sends it with the AI request. The backend relays the request to OpenRouter without persisting the key.

For production deployment, additional security measures should be considered, including:

* User authentication
* HTTPS
* Rate limiting
* Persistent database storage
* CSRF protection
* Secure API key management

## Project Philosophy

The main idea behind this project is:

> You do not need to completely change how you travel. One realistic change can make a meaningful difference when repeated consistently.

Instead of simply telling users to travel greener, the application tries to answer a more practical question:

> What is the smallest change I can realistically make that will have the biggest impact?

## Future Improvements

* Add SQLite or PostgreSQL database support
* Add user authentication
* Add multi-user support
* Import trips from CSV
* Add Google Maps or OpenStreetMap integration
* Add live route calculations
* Add public transportation data
* Improve regional emission factors
* Convert the application into a Progressive Web App
* Add cloud deployment support
* Add user accounts
* Add historical dashboards
* Export analytics as CSV or PDF
* Add additional AI providers
* Add automated monthly carbon reports

## License

This project is currently available without a specified license.

If you plan to make the repository public, consider adding an appropriate open-source license such as the MIT License.

## Authors

Karthik Senigala & Nikhil Penumala

Built with Python, Flask, JavaScript, Chart.js, and a goal of making sustainable travel decisions more practical and personalized.

