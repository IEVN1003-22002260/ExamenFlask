from flask import Flask, render_template, request

#Notas
#enviar y recibir parametros Get y Post

app=Flask(__name__)

#un decorador es poniendo un arroba
@app.route("/") #decorador o ruta
def index():
    titulo="Pagina de Inicio"
    listado = ["Python", "Flask", "Jinja", "HTML", "CSS"]
    return render_template("index.html",titulo=titulo,listado=listado)

@app.route("/operasbas", methods=["GET", "POST"])
def operasbas():
    n1=0
    n2=0
    res=0
    operacion=''
    if request.method=='POST':
        n1=request.form.get('n1')
        n2=request.form.get('n2')
        if request.form.get('operacion')=='sumar':
            res=float(n1)+float(n2)
        elif request.form.get('operacion')=='restar':
            res=float(n1)-float(n2)
        elif request.form.get('operacion')=='multiplicar':
            res=float(n1)*float(n2)
            

    return render_template('operasbas.html', n1=n1, n2=n2, res=res)
      



@app.route("/distancia", methods=["GET", "POST"])
def distancia():
    resultado = 0

    if request.method == 'POST':
        x1 = float(request.form.get('x1'))
        y1 = float(request.form.get('y1'))
        x2 = float(request.form.get('x2'))
        y2 = float(request.form.get('y2'))

        resultado = ((x2 - x1)**2 + (y2 - y1)**2)**0.5

    return render_template('distancia.html', resultado=resultado)

@app.route("/hola") #decorador o ruta
def hola():
    return "<h1> Hola PWA  - IEVN1003</h1>"

#como pasar parametros por url
@app.route("/user/<string:nom>") #decorador o ruta
def user(nom):
    return "<h1> Hola User:{} </h1> ".format(nom)
    #el format sirve para hacer el preformateo


@app.route("/numero/<int:n>") #decorador o ruta
def numero(n):
    return " Numero: {}".format(n)

@app.route("/user/<int:id>/<string:username>")
def username(id,username):
    return "ID:{} nombre:{}".format(id.username)

@app.route("/suma/<float:n1>/<float:n2>")
def func(n1,n2):
    return "La suma es:{}".format(n1+n2)

if __name__=="__main__":
    app.run(debug=True)