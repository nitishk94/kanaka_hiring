from myapp import create_app

app = create_app()

if __name__ == '__main__':
    app.run(ssl_context=('/app/ssl/cert.pem', '/app/ssl/key.pem'), host='0.0.0.0', debug=True)