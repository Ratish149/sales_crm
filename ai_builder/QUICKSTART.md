## Quick Start Checklist

1. **Add API Key to `.env`:**
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   ```

2. **Restart the Server:**
   ```bash
   # Stop current server (Ctrl+C)
   python manage.py runserver
   ```

3. **Test the Health Endpoint:**
   ```bash
   # In another terminal
   curl http://localhost:8000/ai-builder/health/
   # Should return: {"status":"ok","service":"ai_builder"}
   ```

4. **Open the Builder IDE:**
   - Navigate to: `http://localhost:8000/builder/`
   - Look for the **🤖 AI Builder Assistant** panel on the right
   - Type a prompt and click "Send to AI"

5. **Test with a Simple Prompt:**
   ```
   "Create a new file called hello.txt with the text Hello World"
   ```

## Troubleshooting

**Issue: Chat doesn't respond**
- Check that `GOOGLE_API_KEY` is set in `.env`
- Verify the key is valid at https://ai.google.dev/

**Issue: Can't see the chat panel**
- Hard refresh the page (Ctrl+Shift+R)
- Check browser console for JavaScript errors

**Issue: 404 on /ai-builder/run/**
- Ensure server was restarted after adding the app
- Run `python manage.py check` to verify no errors
