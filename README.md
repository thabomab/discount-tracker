# PrcDrop Developer Documentation

## Overview
**PrcDrop** is a discount tracking web application designed to monitor price changes on products across supported e-commerce websites. The app notifies users via email when a price drop is detected. The system is composed of a frontend and a backend, both hosted on AWS, and is designed to be scalable and easy to maintain.

---

## Architecture

### Frontend
- **Hosting**: AWS S3 (static site hosting) delivered via CloudFront.
- **DNS Management**: AWS Route 53.
- **Technology Stack**: 
  - HTML, CSS, and JavaScript.
  - Includes a form for users to input product URLs and their email addresses.
  - Validates inputs before sending data to the backend.

### Backend
- **Hosting**: AWS EC2.
- **Web Server**: Apache with Gunicorn.
- **Task Management**: Celery with Redis as the broker.
- **Framework**: Flask (Python).
- **Core Functions**:
  - Validates and processes user input.
  - Tracks product prices using Selenium and predefined CSS selectors for supported websites.
  - Sends email notifications upon detecting price drops.
  - Logs requests and errors.
- **Endpoints**:
  - `/track (POST)`: Initiates tracking for a product.
  - `/reload-selectors (POST)`: Reloads CSS selectors from a JSON file.
  - `/status (GET)`: Returns service status.

---

## Development Setup

### Prerequisites
- Python 3.8 or later.
- AWS CLI configured with appropriate permissions.
- Redis instance running locally or on a configured endpoint.

### Local Development

#### Frontend
1. Clone the repository.
2. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
3. Open `index.html` in your preferred code editor for customization.
4. Use a local server (e.g., `http-server`) to test changes locally:
   ```bash
   npx http-server .
   ```

#### Backend
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start Redis:
   ```bash
   redis-server
   ```
4. Set environment variables for email credentials and app configuration.
5. Start the backend server:
   ```bash
   flask run
   ```
6. Start Celery:
   ```bash
   celery -A app.celery worker --loglevel=info
   ```

---

## Files and Directories

### Frontend
- `index.html`: Main HTML file.
- `style.css`: Contains all custom styles.
- `script.js`: Includes form validation and API interaction.

### Backend
- `app.py`: Main Flask application.
- `celery_config.py`: Celery setup.
- `logger_config.py`: Logging configuration.
- `price_selectors.json`: Stores domain names and CSS selectors for price tracking.
- `email_config.json`: Email credentials for sending notifications.

---

## Adding Support for a New Website
1. Identify the CSS selector for the price element on the target website.
2. Update `price_selectors.json` with the new domain and selector:
   ```json
   {
       "newsite.com": "CSS_SELECTOR"
   }
   ```
3. Reload selectors by calling the `/reload-selectors` endpoint:
   ```bash
   curl -X POST http://localhost:5000/reload-selectors
   ```
4. Test with a product URL from the new site.

---

## Deployment

### Frontend
1. Upload the frontend files to the configured S3 bucket:
   ```bash
   aws s3 sync ./frontend s3://your-bucket-name
   ```
2. Invalidate the CloudFront cache:
   ```bash
   aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths "/*"
   ```

### Backend
1. SSH into the EC2 instance.
2. Pull the latest changes from the repository.
3. Restart Gunicorn and Celery workers:
   ```bash
   sudo systemctl restart gunicorn
   sudo systemctl restart celery
   ```

---

## Future Enhancements
- **User Profiles**:
  - Add a login system to allow users to manage their tracked items.
  - Store user data in a database.
- **Enhanced Notifications**:
  - Add SMS notifications.
  - Integrate with push notification services.
- **Analytics Dashboard**:
  - Provide users with insights into historical price trends.
- **Improved Selector Management**:
  - Build an admin interface to manage CSS selectors dynamically.

---

## Troubleshooting

### Common Issues
- **Frontend Not Loading**:
  - Verify S3 bucket permissions.
  - Check CloudFront distribution settings.
- **Selectors Not Found**:
  - Ensure `price_selectors.json` is up to date.
  - Use browser developer tools to debug the selector.
- **Email Not Sent**:
  - Verify email credentials in `email_config.json`.
  - Check SMTP server availability.
- **Background Tasks Failing**:
  - Check Celery and Redis logs for errors.

---

## Contact
For support or contributions, contact the PrcDrop development team at [prcdropp@gmail.com](mailto:prcdropp@gmail.com).
