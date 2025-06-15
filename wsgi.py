from app import app

# This is for Vercel
app = app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000) 