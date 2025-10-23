-- seleciona todos os campos

select 
	setor, 
	avg(peso_liquido) as media,
	stddev_samp(peso_liquido) as desvio_padrao,
	stddev_samp(peso_liquido)/avg(peso_liquido) as coeficiente_variacao
from registro
 	group by setor;

