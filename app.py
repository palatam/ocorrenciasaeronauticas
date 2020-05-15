import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_table
import dash_html_components as html
import time
from datetime import datetime as dt
import pandas as pd
import psycopg2
import plotly.graph_objs as go
import re
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

graph_style = {
    'margin-left': '1.25rem',
    'display': 'inline-block'
}

graph_bgcolor = '#ffffff'
plot_bgcolor = graph_bgcolor

## -- IMPORTANDO DADOS --
def get_data():
    data_dict = {'codigo_ocorrencia1': 'ocorrencia_tipo',
            'codigo_ocorrencia2': 'aeronave',
            'codigo_ocorrencia3': 'fator_contribuinte',
            'codigo_ocorrencia4': 'recomendacao',
            }

    df = pd.read_csv('Data/CENIPA/ocorrencia.csv', sep=';', encoding='latin1')
    df['ocorrencia_ano'] = df['ocorrencia_dia'].apply(lambda x: x.split('/')[2])
    df['ocorrencia_mes'] = df['ocorrencia_dia'].apply(lambda x: x.split('/')[1])

    for key, value in data_dict.items():
        df = df.merge(pd.read_csv('Data/CENIPA/{}.csv'.format(value), sep=';', encoding='latin1'),
                        on=key, how='left')

    return df

df = get_data()

## -- FUNÇÕES AUXILIARES --
def get_options(df, df_column):
    dict_list = []
    option_list = list(set(df[df_column].astype(str).tolist()))
    if '***' in option_list: option_list.remove('***')
    if 'nan' in option_list: option_list.remove('nan')
    option_list.sort()
    for row in option_list:
        dict_list.append({'label': row, 'value': row})

    return dict_list

app = dash.Dash(__name__)
server = app.server

## -- CALLBACKS --

@app.callback([Output('graph-output1', 'children'),
                Output('graph-output2', 'children'),
                Output('graph-output3', 'children'),
                Output('graph-output4', 'children'),
                Output('table-output1', 'children')],
                [Input('classificacao_multiselect', 'value'),
                Input('tipo_ocorrencia_multiselect', 'value'),
                Input('area_fator_contribuinte_multiselect', 'value'),
                Input('fator_contribuinte_multiselect', 'value'),
                Input('date-range-picker', 'start_date'),
                Input('date-range-picker', 'end_date'),
                Input('campos_relatorio_multiselect', 'value')])
def generate_objects(classificacao_value, tipo_ocorrencia_value, area_fator_contribuinte_value, fator_contribuinte_value, start_date, end_date, campos_relatorio_value, max_rows=10):

    df = get_data()

    ## FILTROS
    if classificacao_value != None and len(classificacao_value) != 0:
        df = df[df['ocorrencia_classificacao'].isin(classificacao_value)]
    if tipo_ocorrencia_value != None and len(tipo_ocorrencia_value) != 0:
        df = df[df['ocorrencia_tipo'].isin(tipo_ocorrencia_value)]
    if area_fator_contribuinte_value != None and len(area_fator_contribuinte_value) != 0:
        df = df[df['fator_area'].isin(area_fator_contribuinte_value)]
    if fator_contribuinte_value != None and len(fator_contribuinte_value) != 0:
        df = df[df['fator_nome'].isin(fator_contribuinte_value)]
    if start_date != None and len(start_date) != 0 and end_date != None and len(end_date) != 0:
        print(type(start_date))
        df = df[(df['ocorrencia_dia'].astype('datetime64[ns]')>start_date) & (df['ocorrencia_dia'].astype('datetime64[ns]')<end_date)]
    else:
        df = df

    ## GRÁFICOS (TAB 1)
    graph_width = 55
    graph_height = 32

    # Gráfico 1
    temp = df.groupby('ocorrencia_classificacao')
    piedata = go.Pie(labels=list(temp.groups.keys()),values=temp['codigo_ocorrencia'].nunique().tolist())
    Graph1 = dcc.Graph(
            figure={
                'data': [piedata],
                'layout': {
                    'title': 'Quantidade Ocorrências por Classificação',
                    'plot_bgcolor': plot_bgcolor,
                    'paper_bgcolor': graph_bgcolor,
                    'display': 'inline-block',
                    'margin': {
                        't': 40
                    }
                }
            },
            style={'width': '{}rem'.format(graph_width), 'height': '{}rem'.format(graph_height)}
        )

    # Gráfico 2
    temp = df[['codigo_ocorrencia', 'ocorrencia_ano', 'aeronave_fatalidades_total']].drop_duplicates().groupby('ocorrencia_ano')
    Graph2 = dcc.Graph(
            figure={
                'data': [
                    {'x': list(temp['codigo_ocorrencia'].nunique().keys()), 'y': temp['codigo_ocorrencia'].nunique().tolist(), 'type': 'bar', 'name': 'Quantidade Ocorrências'},
                    {'x': list(temp['aeronave_fatalidades_total'].sum().keys()), 'y': temp['aeronave_fatalidades_total'].sum().tolist(), 'type': 'bar', 'name': 'Quantidade Fatalidades'}
                ],
                'layout': {
                    'title': 'Quantidade Ocorrências x Fatalidades por Ano',
                    'plot_bgcolor': plot_bgcolor,
                    'paper_bgcolor': graph_bgcolor,
                    'display': 'inline-block',
                    'margin': {
                        't': 40
                    }
                },

            },
            style={'width': '{}rem'.format(graph_width), 'height': '{}rem'.format(graph_height)}
        )

    # Gráfico 3
    temp = df[['codigo_ocorrencia', 'fator_area']][df['fator_area']!='***'].groupby('fator_area')
    Graph3 = dcc.Graph(
            figure={
                'data': [go.Bar(x=temp['codigo_ocorrencia'].nunique().sort_values().tolist(),
                        y=list(temp['codigo_ocorrencia'].nunique().sort_values().keys()),
                        orientation='h')],
                'layout': {
                    'title': 'Quantidade Ocorrências por área de fator contribuinte',
                    'plot_bgcolor': plot_bgcolor,
                    'paper_bgcolor': graph_bgcolor,
                    'display': 'inline-block',
                    'margin': {
                        't': 30,
                        'l': 175
                    }
                }
            },
            style={'width': '{}rem'.format(graph_width), 'height': '{}rem'.format(graph_height)}
        )

    # Gráfico 4
    rows_to_show = 10
    temp = df.groupby('fator_nome')
    Graph4 = dcc.Graph(
            figure={
                'data': [go.Bar(x=temp['codigo_ocorrencia'].nunique().sort_values().tolist()[-1*max_rows:],
                        y=list(temp['codigo_ocorrencia'].nunique().sort_values().keys())[-1*max_rows:],
                        orientation='h')],
                'layout': {
                    'title': 'Quantidade Ocorrências por fator contribuinte',
                    'plot_bgcolor': plot_bgcolor,
                    'paper_bgcolor': graph_bgcolor,
                    'display': 'inline-block',
                    'margin': {
                        't': 30,
                        'l': 200
                    }
                }
            },
            style={'width': '{}rem'.format(graph_width), 'height': '{}rem'.format(graph_height)}
        )


    ## TABLES (TAB 2)
    # temp = df[['codigo_ocorrencia', 'ocorrencia_dia', 'ocorrencia_classificacao', 'fator_area', 'fator_nome']].drop_duplicates()
    temp = df[campos_relatorio_value].drop_duplicates()
    Table1 = dash_table.DataTable(
            columns=[{'name': i, 'id': i} for i in temp.columns.values],
            style_table={'height': '50rem', 'width': '110rem', 'overflowY': 'auto'},
            sort_action='native',
            sort_mode='multi',
            filter_action='native',
            export_format='csv',
            export_headers='ids',
            data=temp.to_dict('rows')
    )

    return [Graph1, Graph2, Graph3, Graph4, Table1]


app.layout = html.Div([
    ## START LEFT PANEL
    html.Div(style={'background-color': '#ffffff',
                    'border-width': '2px',
                    'border-radius': '5px',
                    'border-style': 'solid',
                    'padding-left': '10px',
                    'padding-right': '10px'},
        className='three columns div-users-controls',
        children=[
            html.H4(children='Ocorrências Aeronáuticas',
                    style={'font-weight': 'bold', 'display': 'inline-block', 'padding-left': '2px', 'padding-top': '5px'}),

            html.P(children='Relatórios em forma visual com dados fornecidos pelo CENIPA.',
                    style={'width': '100%',  'display': 'inline-block', 'padding-left': '5px'}),

            html.P(children='Ocorrências de 03-Jan-2010 até 31-Dec-2019. ',
                    style={'width': '100%',  'display': 'inline-block', 'padding-left': '5px'}),

            # FILTROS
            html.P(children='Filtros Disponíveis',
                    style={'font-weight': 'bold', 'width': '100%',  'display': 'inline-block', 'padding-left': '5px'}),

            html.P('Período:',
                    style={'display': 'inline-block', 'padding-left': '5px'}),
            dcc.DatePickerRange(
                id='date-range-picker',
                start_date_placeholder_text='Início',
                end_date_placeholder_text='Fim',
                display_format='DD MMM YYYY',
                clearable=True,
                style={'display': 'inline-block'}
            ),

            html.P('Classificação da Ocorrência:',
                    style={'width': '100%', 'display': 'inline-block', 'padding-left': '5px'}),
            dcc.Dropdown(
                id='classificacao_multiselect',
                options=get_options(df, 'ocorrencia_classificacao'),
                value=None,
                multi=True,
                clearable=True,
                style={'width': '95%', 'display': 'inline-block'}
            ),

            html.P('Tipo da Ocorrência:',
                    style={'width': '100%', 'display': 'inline-block', 'padding-left': '5px'}),
            dcc.Dropdown(
                id='tipo_ocorrencia_multiselect',
                options=get_options(df, 'ocorrencia_tipo'),
                optionHeight=50,
                value=None,
                multi=True,
                clearable=True,
                style={'width': '95%', 'display': 'inline-block'}
            ),

            html.P('Área Fator Contribuinte:',
                    style={'width': '100%', 'display': 'inline-block', 'padding-left': '5px'}),
            dcc.Dropdown(
                id='area_fator_contribuinte_multiselect',
                options=get_options(df, 'fator_area'),
                optionHeight=50,
                value=None,
                multi=True,
                clearable=True,
                style={'width': '95%',  'display': 'inline-block'}
            ),
            #
            html.P('Fator Contribuinte:',
                    style={'width': '100%', 'display': 'inline-block', 'padding-left': '5px'}),
            dcc.Dropdown(
                id='fator_contribuinte_multiselect',
                options=get_options(df, 'fator_nome'),
                optionHeight=50,
                value=None,
                multi=True,
                clearable=True,
                style={'width': '95%',  'display': 'inline-block'}
            ),

            html.P(' '),
            html.P('Criado por: Rodrigo Martins Pires',
                    style={'font-style': 'italic', 'width': '100%', 'display': 'inline-block', 'padding-left': '5px', 'padding-top': '10px'}),

            html.P('rodrigo.pires@palatinoamericana.com',
                    style={'font-style': 'italic', 'width': '100%', 'display': 'inline-block', 'padding-left': '5px'}),

            html.P('Fonte: http://www.dados.gov.br/dataset/ocorrencias-aeronauticas-da-aviacao-civil-brasileira',
                    style={'font-style': '', 'width': '100%', 'display': 'inline-block', 'padding-left': '5px'})
    ]),
    ## END LEFT PANEL

    ## START MAIN PANEL

    html.Div(children=[
            dcc.Tabs(id='main_tabs',
                value='tab-1',
                style={'padding-left': '10px',
                        'padding-right': '5px',
                        'padding-bottom': '5px',
                        'padding-top': '0px'},
                children=[
                    dcc.Tab(label='Gráficos',
                            value='tab-1',
                            children=[
                                # Gráfico 1
                                html.Div(style=graph_style,
                                        id='graph-output1'),

                                # Gráfico 2
                                html.Div(style=graph_style,
                                        id='graph-output2'),

                                # Gráfico 3
                                html.Div(style=graph_style,
                                        id='graph-output3'),

                                # Gráfico 4
                                html.Div(style=graph_style,
                                        id='graph-output4'),
                        ]),
                    dcc.Tab(label='Relatório',
                            value='tab-2',
                            children=[
                                html.P('Campos a mostrar:',
                                        style=graph_style),
                                dcc.Dropdown(
                                    id='campos_relatorio_multiselect',
                                    options=[{'label': row, 'value': row} for row in list(df.columns.values)],
                                    optionHeight=50,
                                    value=['codigo_ocorrencia', 'ocorrencia_dia', 'ocorrencia_classificacao', 'fator_area', 'fator_nome'],
                                    multi=True,
                                    style={'margin-left': '0.5rem', 'width': '97.5%',  'display': 'inline-block'}
                                ),
                                html.Div(id='table-output1',
                                        style=graph_style),
                            ]),
                    # dcc.Tab(label='Tab 3', value='tab-3'),
            ])
    ])
    ## END MAIN PANEL
])

if __name__ == '__main__':
    app.run_server()
