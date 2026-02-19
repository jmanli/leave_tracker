# Deployment Guide for Render

## Automated Deployment Steps

### 1. Push to GitHub
```bash
git add .
git commit -m "Configure for Render PostgreSQL deployment"
git push origin main
```

### 2. Connect Repository to Render
1. Go to https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select `leave_tracker` repository

### 3. Configure Web Service
Use these settings:
- **Name**: leave-tracker-app
- **Runtime**: Python 3
- **Build Command**: `pip install -r requirements.txt && flask db upgrade && python init_db.py`
- **Start Command**: `gunicorn app:app`

### 4. Environment Variables
Add these in Render dashboard (or use render.yaml):

```
DATABASE_URL=postgresql://leave_tracker_db_u4kr_user:NM9cLVXmvLUspsMV37OVf4woCQiWTOxl@dpg-d6bd438gjchc73ahtlkg-a/leave_tracker_db_u4kr
SECRET_KEY=[auto-generate or use your own]
PYTHON_VERSION=3.11.0
UPLOAD_FOLDER=/opt/render/project/src/static/uploads
MAX_CONTENT_LENGTH=16000000
```

### 5. Deploy
Render will automatically:
- Install dependencies
- Run database migrations (`flask db upgrade`)
- Initialize database and create admin user (`python init_db.py`)
- Start the application (`gunicorn app:app`)

### 6. First Login
After deployment:
- **URL**: https://leave-tracker-app.onrender.com
- **Email**: admin@company.com
- **Password**: Admin123!
- **⚠️ CHANGE PASSWORD IMMEDIATELY after first login!**

## Database Information
- **Type**: PostgreSQL 
- **Database**: leave_tracker_db_u4kr
- **User**: leave_tracker_db_u4kr_user
- **Host**: dpg-d6bd438gjchc73ahtlkg-a
- **Connection**: Internal (for Render services)

## Important Notes

### Free Tier Limitations
- Service spins down after 15 minutes of inactivity
- First request after sleep: ~30 seconds to wake up
- 750 hours/month of runtime
- No shell access (handled by init_db.py automation)

### File Uploads
⚠️ **Warning**: Free tier has ephemeral storage. Uploaded files will be deleted on restart.

**Solutions**:
1. Add a persistent disk (costs extra)
2. Use cloud storage (AWS S3, Cloudinary, etc.)

### Monitoring
- Check deployment logs in Render dashboard
- Look for "✅ Admin user created successfully!" message
- Verify database tables are created

## Troubleshooting

### Database Connection Errors
Ensure `DATABASE_URL` environment variable is set correctly in Render.

### Migration Errors
If migrations fail, check logs. May need to delete `migrations/` folder and reinitialize:
```bash
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Admin User Not Created
Check build logs for `init_db.py` output. Should see success messages.

## Local Testing with PostgreSQL
To test locally before deploying:
```bash
pip install -r requirements.txt
flask db upgrade
python init_db.py
flask run
```

Visit: http://localhost:5000
