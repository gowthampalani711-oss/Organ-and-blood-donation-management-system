<?php
// LifeSaver Organ & Blood Donation Management System
// Automatic redirect to Flask backend server

$flask_url = "http://localhost:5000/";
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LifeSaver - Starting Application...</title>
    <meta http-equiv="refresh" content="2;url=<?php echo $flask_url; ?>">
    <link rel="stylesheet" href="static/css/style.css">
    <style>
        body {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #F8FAFC;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 1.5rem;
        }
        .portal-card {
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.1);
            border: 1px solid #E2E8F0;
            max-width: 520px;
            width: 100%;
            padding: 2.5rem;
            text-align: center;
        }
        .portal-icon {
            font-size: 3rem;
            color: #E63946;
            margin-bottom: 1rem;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        h2 {
            color: #1D3557;
            margin-bottom: 0.5rem;
            font-size: 1.6rem;
        }
        p {
            color: #64748B;
            font-size: 0.95rem;
            line-height: 1.5;
            margin-bottom: 1.5rem;
        }
        .btn-launch {
            display: inline-block;
            background: #1D3557;
            color: #ffffff;
            padding: 0.85rem 1.75rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.2s ease;
            box-shadow: 0 4px 12px rgba(29, 53, 87, 0.2);
        }
        .btn-launch:hover {
            background: #457B9D;
            transform: translateY(-2px);
        }
        .cmd-hint {
            margin-top: 1.5rem;
            background: #F1FAEE;
            border: 1px dashed #A8DADC;
            padding: 0.85rem;
            border-radius: 8px;
            font-size: 0.85rem;
            color: #1D3557;
            text-align: left;
        }
        .cmd-hint code {
            display: block;
            background: #1D3557;
            color: #A8DADC;
            padding: 0.4rem 0.6rem;
            border-radius: 4px;
            margin-top: 0.4rem;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="portal-card">
        <div class="portal-icon">♥</div>
        <h2>LifeSaver Network</h2>
        <p>Redirecting to the Python Flask application server at <strong>http://localhost:5000</strong>...</p>
        
        <a href="<?php echo $flask_url; ?>" class="btn-launch">
            Open Application (localhost:5000) &rarr;
        </a>

        <div style="margin-top: 1rem;">
            <a href="templates/index.html" style="font-size: 0.85rem; color: #457B9D; text-decoration: underline;">
                Or view Static Preview (templates/index.html)
            </a>
        </div>

        <div class="cmd-hint">
            <strong>Note for Developer:</strong> This system runs on Python Flask. If the page doesn't load, make sure the backend is running in your terminal:
            <code>python app.py</code>
        </div>
    </div>
</body>
</html>
