from flask import *
import psycopg2

app = Flask(__name__)
DATABASE_CONNECTION = "dbname=projeto user=postgres password=postgres host=localhost"

# @app.route("/qtde_por_mes_ano/<int:ano>")
@app.route("/qtde_por_mes_ano", methods = ['GET', 'POST'])
def qtde_por_mes_ano():        
    if request.method == 'POST':
        ano = request.form['ano']
        label_name = "Meses de "+str(ano) 
        name = "Meses"
        labels = []
        vet = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        data = []   
        conn = psycopg2.connect(DATABASE_CONNECTION)
        cur = conn.cursor()
        cur.execute("""
        SELECT extract(year from cast(data_hora as date)) as ano,  
             extract(month from cast(data_hora as date))::integer as mes, 
             count(*) as qtde 
                 from registro where extract(year from cast(data_hora as date)) = %s 
                 group by extract(year from cast(data_hora as date)), 
                extract(month from cast(data_hora as date)) 
                     order by extract(month from cast(data_hora as date)),  extract(year from cast(data_hora as date));
                     """, [ano])
        rows = cur.fetchall()
        for row in rows:
            labels.append(vet[row[1]-1])
            data.append(int(row[2]))
        cur.close()
        conn.close()           
        # return render_template('grafico.html',  name=name, label_name = label_name, labels=labels, data=data)   
        return render_template('grafico_bar.html', label_name = label_name, labels=labels, data=data)   
    else:
        return render_template('qtde_por_mes_ano.html')   
    
'''
select setor, 
	avg(peso_embalagem_liquido_corrigido), 
	cast(STDDEV_SAMP(peso_embalagem_liquido_corrigido)/avg(peso_embalagem_liquido_corrigido) * 100.0 as numeric(100,2)) as coeficiente_variacao_porcentagem
from 
	registro 
group by 
	setor 
order by avg(peso_embalagem_liquido_corrigido) desc;
'''

@app.route("/media_por_setor")
def media_por_setor():
    sql = "select setor, avg(peso_embalagem_liquido_corrigido) from registro group by setor order by avg(peso_embalagem_liquido_corrigido) desc;"
    label_name = "Média Peso Líquido/Setores" 
    name = "Média"    
    labels = []
    data = []   
    conn = psycopg2.connect(DATABASE_CONNECTION)
    cur = conn.cursor()
    cur.execute(sql)    
    rows = cur.fetchall()
    for row in rows:
        labels.append(row[0])
        data.append(int(row[1]))
    cur.close()
    conn.close()          
    # return render_template('grafico.html', name=name, label_name = label_name, labels=labels, data=data)     
    return render_template('grafico.html', label_name = label_name, labels=labels, data=data)   


@app.route("/qtde_por_ano")
def qtde_por_ano():
    label_name = "Anos" 
    name = "Ano"
    sql = "SELECT extract(year from cast(data_hora as date)) as ano, count(*) as qtde from registro group by extract(year from cast(data_hora as date)) order by extract(year from cast(data_hora as date));"
    labels = []
    data = []   
    conn = psycopg2.connect(DATABASE_CONNECTION)
    cur = conn.cursor()
    cur.execute(sql)    
    rows = cur.fetchall()
    for row in rows:
        labels.append(row[0])
        data.append(int(row[1]))
    cur.close()
    conn.close()          
    # return render_template('grafico.html', name=name, label_name = label_name, labels=labels, data=data)     
    return render_template('grafico_bar.html', label_name = label_name, labels=labels, data=data)   

@app.route("/fornecedores_clientes")
def fornecedores_clientes():
    label_name = "fornecedores_clientes"
    name = "fornecedores_clientes"
    labels = []
    data = []   
    conn = psycopg2.connect(DATABASE_CONNECTION)
    cur = conn.cursor()
    cur.execute("SELECT fornecedor_cliente, count(*) from registro group by fornecedor_cliente order by fornecedor_cliente;")    
    rows = cur.fetchall()
    for row in rows:
        labels.append(row[0])
        data.append(int(row[1]))
    cur.close()
    conn.close()        
    # return render_template('grafico.html', name=name, label_name = label_name, labels=labels, data=data)   
    return render_template('grafico_pizza.html', label_name = label_name, labels=labels, data=data)   
    


@app.route("/produtos")
def produtos():
    label_name = "Produtos"
    name = "Produtos"
    labels = []
    data = []   
    conn = psycopg2.connect(DATABASE_CONNECTION)
    cur = conn.cursor()
    cur.execute("SELECT produto, count(*) from registro group by produto order by produto;")    
    rows = cur.fetchall()
    for row in rows:
        labels.append(row[0])
        data.append(int(row[1]))
    cur.close()
    conn.close()        
    # return render_template('grafico.html', name=name, label_name = label_name, labels=labels, data=data)   
    return render_template('grafico_bar.html', label_name = label_name, labels=labels, data=data)   



@app.route("/media_peso_por_mes", methods = ['GET', 'POST'])
def media_peso_por_mes():
    if (request.method == 'POST'):
        ano = request.form['ano']
        label_name = "Média de Peso por Mês em "+str(ano)
        name = "Média de Peso por Mês em "+str(ano)    
        labels = []
        data = []   
        conn = psycopg2.connect(DATABASE_CONNECTION)
        cur = conn.cursor()
        cur.execute(" select extract(month from data_hora) mes, avg(peso_entrada) as media from registro where extract(year from data_hora) = %s group by extract(month from data_hora) order by extract(month from data_hora);", [ano])    
        rows = cur.fetchall()
        vet = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        for row in rows:
            labels.append(vet[int(row[0])-1])
            data.append(float(row[1]))
        cur.close()
        conn.close()        
        # return render_template('grafico.html', name=name, label_name = label_name, labels=labels, data=data)   
        return render_template('grafico_bar.html', label_name = label_name, labels=labels, data=data)   
    else:
        return render_template('media_peso_por_mes.html')               

@app.route("/lista")
def lista():
    sql = "select * from registro where extract(year from data_hora) = 2024 and	extract(month from data_hora) = 5 order by ticket;"
    conn = psycopg2.connect(DATABASE_CONNECTION)
    cur = conn.cursor()
    cur.execute(sql)    
    rows = cur.fetchall()
    print(rows)
    cur.close()
    conn.close()  
    return render_template("lista.html", vetRegistro = rows, mes = "Maio", ano = 2024)

   

@app.route("/setores")
def setores():
    label_name = "Setores"
    name = "Setores"
    labels = []
    data = []   
    conn = psycopg2.connect(DATABASE_CONNECTION)
    cur = conn.cursor()
    cur.execute("SELECT setor, count(*) from registro group by setor order by setor;")    
    rows = cur.fetchall()
    for row in rows:
        labels.append(row[0])
        data.append(int(row[1]))
    cur.close()
    conn.close()        
    # return render_template('grafico.html', name=name, label_name = label_name, labels=labels, data=data)   
    return render_template('grafico.html', label_name = label_name, labels=labels, data=data)   

@app.route("/teste")
def teste():    
    return {
        "username": "igor",
        "email": "igor.pereira@riogrande.ifrs.edu.br"
    }

@app.route("/teste_pagina")
def teste_pagina():    
    return render_template('teste.html')   

    
@app.route("/")
def index():
    # html = setores()
    # html = html + qtde_por_ano()
    # html = html + qtde_por_mes_ano(2024)        
    # return render_template('layout.html', html=html)    
    return render_template('index.html')

    # run
    #  python3.12 -m venv .venv
    # . .venv/bin/activate
    # pip3 install -r requirements.txt
    # flask --app index run

    # port already use
    # lsof -i :5000
    # sudo kill <pid here> # ex: sudo kill 19253
