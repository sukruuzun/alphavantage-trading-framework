# 🚀 Deployment Guide

## Environment Variables

Set these environment variables in your hosting platform:

```bash
FLASK_ENV=production
SECRET_KEY=your-secret-key-here-make-it-long-and-random
DATABASE_URL=postgresql://... (automatically provided by Heroku)
```

## Heroku Deployment

1. Create Heroku account and install Heroku CLI
2. Login: `heroku login`
3. Create app: `heroku create your-app-name`
4. Add PostgreSQL: `heroku addons:create heroku-postgresql:mini`
5. Set environment variables:
   ```bash
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY="your-secret-key-here"
   ```
6. Deploy: `git push heroku main`

## Railway Deployment

1. Connect GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically on push

## Render Deployment

1. Connect GitHub repository to Render
2. Set environment variables in Render dashboard
3. Use build command: `pip install -r web_requirements.txt`
4. Use start command: `gunicorn web_app:app` 