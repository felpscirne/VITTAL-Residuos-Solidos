import argparse
import os
import random
import string
from datetime import UTC, datetime, timedelta

import pandas as pd

COLUMNS_NAMES = [
    'ticket', 'placa', 'data_hora', 'produto', 'transportadora', 'fornecedor_cliente',
    'peso_entrada', 'peso_saida', 'peso_liquido', 'peso_embalagem_liquido',
    'peso_embalagem_liquido_corrigido', 'peso_nota_fiscal', 'placa_veiculo',
    'diferenca_peso', 'diferenca_peso_porcentagem', 'nro_nota_fiscal', 'setor',
    'destino_procedencia',
]

MONTH_MAP = {
    'JANEIRO': 1,
    'FEVEREIRO': 2,
    'MARCO': 3,
    'ABRIL': 4,
    'MAIO': 5,
    'JUNHO': 6,
    'JULHO': 7,
    'AGOSTO': 8,
    'SETEMBRO': 9,
    'OUTUBRO': 10,
    'NOVEMBRO': 11,
    'DEZEMBRO': 12,
}

SETORES = [
    'CANDIOTA',
    'ACERTO DE PESO',
    'SETOR NORTE',
    'SETOR SUL',
    'SETOR LESTE',
    'SETOR OESTE',
    'PATIO CENTRAL',
]

PRODUTOS = [
    'RESIDUO DOMICILIAR',
    'RESIDUO RECICLAVEL',
    'RESIDUO ORGANICO',
    'ENTULHO LEVE',
    'PODA URBANA',
    'REJEITO MISTO',
    'RESIDUO HOSPITALAR',
]

EMPRESAS = [
    'EMPRESA ALFA',
    'EMPRESA BETA',
    'SECRETARIA OBRAS',
    'SECRETARIA SAUDE',
    'AUTARQUIA LIMPEZA',
    'COOPERATIVA DELTA',
    'UNIDADE CENTRAL',
]

TRANSPORTADORAS = [
    'TRANSLOG A',
    'TRANSLOG B',
    'FROTA MUNICIPAL',
    'TRANSPORTE RIO',
    'OPERACAO OMEGA',
]

DESTINOS = ['TRIAGEM', 'ATERRO CONTROLADO', 'USINA', 'CENTRO DE TRANSBORDO', 'ESTACAO NORTE']


def infer_month_year_from_filename(filename: str):
    upper = filename.upper()
    month = 1
    year = 2024

    for name, num in MONTH_MAP.items():
        if name in upper:
            month = num
            break

    digits = ''.join(ch if ch.isdigit() else ' ' for ch in upper).split()
    if digits:
        candidates = [int(d) for d in digits if len(d) == 4]
        if candidates:
            year = candidates[0]

    return month, year


def random_plate(rng: random.Random):
    if rng.random() < 0.5:
        letters = ''.join(rng.choice(string.ascii_uppercase) for _ in range(3))
        digits = ''.join(rng.choice(string.digits) for _ in range(4))
        return f'{letters}-{digits}'

    letters = ''.join(rng.choice(string.ascii_uppercase) for _ in range(3))
    return f'{letters}{rng.randint(0,9)}{rng.choice(string.ascii_uppercase)}{rng.randint(0,9)}{rng.randint(0,9)}'


def generate_fake_dataframe(row_count: int, month: int, year: int, ticket_start: int, rng: random.Random):
    start = datetime(year=year, month=month, day=1, hour=0, minute=0)
    if month == 12:
        end = datetime(year=year + 1, month=1, day=1, hour=0, minute=0)
    else:
        end = datetime(year=year, month=month + 1, day=1, hour=0, minute=0)

    total_seconds = int((end - start).total_seconds())

    rows = []
    for i in range(row_count):
        ticket = ticket_start + i
        dt = start + timedelta(seconds=rng.randint(0, max(total_seconds - 1, 1)))

        setor = rng.choice(SETORES)
        produto = rng.choice(PRODUTOS)
        fornecedor = rng.choice(EMPRESAS)
        transportadora = rng.choice(TRANSPORTADORAS) if rng.random() > 0.08 else None
        placa = random_plate(rng)
        placa_veiculo = placa if rng.random() > 0.1 else random_plate(rng)

        peso_entrada = round(rng.uniform(800.0, 36000.0), 2)
        tara = round(rng.uniform(200.0, 18000.0), 2)
        if tara > peso_entrada:
            peso_entrada, tara = tara, peso_entrada

        peso_saida = tara
        peso_liquido = round(max(peso_entrada - peso_saida, 0.0), 2)
        embalagem = round(rng.uniform(0.0, 1200.0), 2)
        peso_embalagem_liquido = round(max(peso_liquido + embalagem, 0.0), 2)
        peso_embalagem_liquido_corrigido = round(max(peso_embalagem_liquido - rng.uniform(0, 80), 0.0), 2)

        if rng.random() < 0.15:
            peso_nota_fiscal = 0.0
        else:
            variacao = rng.uniform(-0.08, 0.08)
            peso_nota_fiscal = round(max(peso_embalagem_liquido_corrigido * (1 + variacao), 0.0), 2)

        diferenca_peso = round(peso_embalagem_liquido_corrigido - peso_nota_fiscal, 2)
        if peso_nota_fiscal > 0:
            diferenca_percentual = round((diferenca_peso / peso_nota_fiscal) * 100, 2)
        else:
            diferenca_percentual = None

        rows.append(
            {
                'ticket': ticket,
                'placa': placa,
                'data_hora': dt,
                'produto': produto,
                'transportadora': transportadora,
                'fornecedor_cliente': fornecedor,
                'peso_entrada': peso_entrada,
                'peso_saida': peso_saida,
                'peso_liquido': peso_liquido,
                'peso_embalagem_liquido': peso_embalagem_liquido,
                'peso_embalagem_liquido_corrigido': peso_embalagem_liquido_corrigido,
                'peso_nota_fiscal': peso_nota_fiscal,
                'placa_veiculo': placa_veiculo,
                'diferenca_peso': diferenca_peso,
                'diferenca_peso_porcentagem': diferenca_percentual,
                'nro_nota_fiscal': f'NF-{year}{month:02d}-{ticket}',
                'setor': setor,
                'destino_procedencia': rng.choice(DESTINOS),
            }
        )

    return pd.DataFrame(rows, columns=COLUMNS_NAMES)


def main():
    parser = argparse.ArgumentParser(description='Generate synthetic .ods sheets based on existing files.')
    parser.add_argument('--source-dir', default='sheets', help='Directory with original sheets')
    parser.add_argument('--target-dir', default='sheets_fake', help='Directory to write synthetic sheets')
    parser.add_argument('--seed', type=int, default=20260408, help='Random seed for reproducible generation')
    args = parser.parse_args()

    rng = random.Random(args.seed)

    if not os.path.exists(args.source_dir):
        raise SystemExit(f'Source directory not found: {args.source_dir}')

    os.makedirs(args.target_dir, exist_ok=True)

    input_files = sorted(
        f for f in os.listdir(args.source_dir)
        if f.lower().endswith('.ods') and not f.startswith('~')
    )

    if not input_files:
        print('No .ods files found in source directory.')
        return

    ticket_base = 100000

    for idx, filename in enumerate(input_files):
        source_path = os.path.join(args.source_dir, filename)
        target_path = os.path.join(args.target_dir, filename)

        source_df = pd.read_excel(source_path, engine='odf', skiprows=2)
        row_count = len(source_df)

        month, year = infer_month_year_from_filename(filename)
        fake_df = generate_fake_dataframe(
            row_count=row_count,
            month=month,
            year=year,
            ticket_start=ticket_base + idx * 10000,
            rng=rng,
        )

        with pd.ExcelWriter(target_path, engine='odf') as writer:
            fake_df.to_excel(writer, index=False, sheet_name='Sheet1', startrow=2)

        print(f'Generated: {target_path} | rows={row_count}')


if __name__ == '__main__':
    main()
