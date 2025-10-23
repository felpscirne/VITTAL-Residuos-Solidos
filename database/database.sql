DROP DATABASE IF EXISTS projeto;

CREATE DATABASE projeto;

\c projeto;


CREATE TABLE registro (
       ticket serial primary key,       
       placa text,
       data_hora timestamp,
       produto text,
       transportadora text,
       fornecedor_cliente text,
       peso_entrada real,
       peso_saida real,
       peso_liquido real,
       peso_embalagem_liquido real,
       peso_embalagem_liquido_corrigido real,
       peso_nota_fiscal real,
       placa_veiculo text,
       diferenca_peso real,
       diferenca_peso_porcentagem real,
       nro_nota_fiscal text,
       setor text,
       destino_procedencia text
);
 
