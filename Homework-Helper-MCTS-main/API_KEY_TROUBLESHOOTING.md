# API Key Troubleshooting Guide

## Problem: 404 NOT_FOUND Error for Models

**Error Message:**
```
models/gemini-1.5-flash is not found for API version v1beta
```

**Cause:** Your API key doesn't have access to the Generative AI models because:
1. The API key wasn't created with the Generative AI API enabled
2. The API needs to be explicitly enabled in your Google Cloud project
3. The key might have insufficient permissions

---

## Solution: Create a Proper API Key

### Method 1: Using Google AI Studio (EASIEST - Recommended)

1. **Go to:** https://aistudio.google.com/app/apikey
2. **Click:** "Create API Key"
3. **Choose:** "Create API key in new project"
4. **Click:** "Create API key in Google Cloud"
5. A new window opens to Google Cloud Console
6. **Copy** the generated API key
7. **Paste** in your `.env` file:
   ```
   GOOGLE_API_KEY=your_new_key_here
   ```
8. **Save** and restart the app

✅ **This method automatically enables all required APIs**

---

### Method 2: Using Google Cloud Console (MANUAL)

If Method 1 doesn't work:

1. **Go to:** https://console.cloud.google.com/
2. **Create a New Project:**
   - Click project dropdown → "New Project"
   - Name: "Homework Helper"
   - Click "Create"
3. **Enable the API:**
   - Search for "Generative Language API"
   - Click the result
   - Click "Enable"
4. **Create API Key:**
   - Go to: Credentials (left sidebar)
   - Click "Create Credentials" → "API Key"
   - Copy the key
5. **Configure the Key:**
   - Click the key to edit it
   - Under "Restrict key to APIs":
     - Uncheck "Restrict to a set of APIs"
     - OR select "Generative Language API"
   - Save
6. **Update your `.env` file:**
   ```
   GOOGLE_API_KEY=your_new_key_here
   ```

---

## Testing Your API Key

After updating your `.env` file, restart the app and it will automatically test the key:

```bash
# Restart the app
cd C:\Users\DELL\OneDrive\Desktop\agent\HomeworkHelperAgent
venv_new\Scripts\Activate.ps1
python app.py
```

The app will output:
```
[INIT] Trying model: gemini-1.5-flash
[INIT] [OK] Using model: gemini-1.5-flash
[INIT] [OK] Using embedding model: models/text-embedding-004
[INIT] [OK] LLM and embeddings model initialized
```

---

## Checklist

- [ ] API key created from https://aistudio.google.com/app/apikey
- [ ] Key is 39 characters long (starts with `AIzaSy`)
- [ ] `.env` file updated with new key
- [ ] App restarted after updating `.env`
- [ ] No error messages about PERMISSION_DENIED or NOT_FOUND

---

## Still Having Issues?

1. **Check API Key Format:**
   - Should start with `AIzaSy`
   - Should be exactly 39 characters
   - No extra spaces

2. **Verify `.env` File:**
   ```bash
   type .env
   ```
   Should show: `GOOGLE_API_KEY=AIzaSy...`

3. **Check Recent Activity:**
   - Visit: https://aistudio.google.com/app/apikey
   - See if your key shows any errors or usage

4. **Try a Completely New Key:**
   - Delete the old key from Google AI Studio
   - Create a brand new one
   - Test immediately

---

## Quick Fix Script

Run this PowerShell command to update the `.env` file:

```powershell
# Replace YOUR_NEW_KEY_HERE with your actual key
$newKey = "YOUR_NEW_KEY_HERE"
(Get-Content .env) -replace "GOOGLE_API_KEY=.*", "GOOGLE_API_KEY=$newKey" | Set-Content .env

# Verify
Get-Content .env
```

Then restart the app!
