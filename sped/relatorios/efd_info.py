# -*- coding: utf-8 -*-

Autor = 'Claudio Fernandes de Souza Rodrigues (claudiofsr@yahoo.com)'
Data  = '28 de Fevereiro de 2020 (início: 10 de Janeiro de 2020)'

import os, re, sys, itertools, csv
import xlsxwriter # pip install xlsxwriter
from datetime import datetime
from time import time, sleep
from sped.efd.pis_cofins.arquivos import ArquivoDigital as ArquivoDigital_PIS_COFINS
from sped.efd.icms_ipi.arquivos   import ArquivoDigital as ArquivoDigital_ICMS_IPI
from sped.relatorios.efd_tabelas  import EFD_Tabelas
from sped.campos import CampoData, CampoCNPJ, CampoCPF, CampoCPFouCNPJ, CampoChaveEletronica, CampoNCM

# Versão mínima exigida: python 3.6.0
python_version = sys.version_info
if python_version < (3,6,0):
	print('versão mínima exigida do python é 3.6.0')
	print('versão atual', "%s.%s.%s" % (python_version[0],python_version[1],python_version[2]))
	exit()

class My_Switch:
	"""
	Definir, apenas uma vez, um dicionário ao invés de utilizar vários 'if/then/else' a cada
	execução de formatar_valor():
	dict[key] = funtion_key(value)
	Ao escolher uma chave, o dicionário aplica uma função (que depende da chave) sobre o valor
	Esta construção possui Ordem O(1).
	Caso fossem utilizados vários if/then/else (ou switch) a ordem seria O(N), que é mais lento!
	"""

	@staticmethod
	def funcao_identidade(chave):
		return chave

	@staticmethod
	def formatar_linhas(numero):
		return f'{int(numero):09d}'

	@staticmethod
	def formatar_mes(mes_num):
		try:
			mes_num = f'{int(mes_num):02d}'
			return f'{EFD_Tabelas.tabela_mes_nominal[mes_num]}'
		except:
			return mes_num
	
	@staticmethod
	def formatar_registro(registro):
		try:
			return f'{registro} - {EFD_Tabelas.tabela_info_do_registro[registro]}'
		except:
			reg = registro[0]
			return f'{registro} - {EFD_Tabelas.tabela_info_do_registro[reg]}'
	
	@staticmethod
	def formatar_cfop(cfop):
		try:
			cfop = f'{int(cfop):04d}'
			return f'{cfop} - {EFD_Tabelas.tabela_cfop_descricao[cfop]}'
		except:
			return cfop
	
	@staticmethod
	def formatar_cst_contrib(codigo_cst):
		try:
			codigo_cst = f'{int(codigo_cst):02d}'
			return f'{codigo_cst} - {EFD_Tabelas.tabela_cst_contrib[codigo_cst]}'
		except:
			return codigo_cst

	@staticmethod
	def formatar_cst_icms(codigo_cst):
		try:
			codigo_cst = f'{int(codigo_cst):03d}'
			return f'{codigo_cst} - {EFD_Tabelas.tabela_cst_icms[codigo_cst]}'
		except:
			return codigo_cst
	
	@staticmethod
	def formatar_nbc(natureza_bc):
		try:
			natureza_bc = f'{int(natureza_bc):02d}'
			return f'{natureza_bc} - {EFD_Tabelas.tabela_bc_do_credito[natureza_bc]}'
		except:
			return natureza_bc
	
	@staticmethod
	def formatar_tipo(tipo_do_item):
		try:
			tipo_do_item = f'{int(tipo_do_item):02d}'
			return f'{tipo_do_item} - {EFD_Tabelas.tabela_tipo_do_item[tipo_do_item]}'
		except:
			return tipo_do_item
	
	@staticmethod
	def formatar_mod(doc_fiscal):
		try:
			return f'{doc_fiscal} - {EFD_Tabelas.tabela_modelos_documentos_fiscais[doc_fiscal]}'
		except:
			return doc_fiscal

	@staticmethod
	def formatar_valores_reais(valor):
		try:
			return float(valor)
		except:
			valor = valor.replace( '.', ''  ) # 4.218.239,19 --> 4218239,19
			valor = valor.replace( ',', '.' ) #   4218239,19 --> 4218239.19
			return float(valor)
	
	@staticmethod
	def formatar_datas(data):
		date_time = datetime.strptime(data, "%d/%m/%Y") # dd/mm/aaaa
		return date_time
	
	# initialize the attributes of the class
	
	def __init__(self, lista_de_colunas, verbose=False):

		self.lista_de_colunas = lista_de_colunas

		self.verbose = verbose

		self.dicionario = {}
	
	def formatar_colunas_do_arquivo_csv(self):

		for nome_da_coluna in self.lista_de_colunas:
			
			match_linha = re.search(r'^Linhas', nome_da_coluna, flags=re.IGNORECASE)
			match_mes   = re.search(r'^Mês do Período', nome_da_coluna, flags=re.IGNORECASE)
			match_reg   = re.search(r'^REG', nome_da_coluna, flags=re.IGNORECASE)
			match_cfop  = re.search(r'^CFOP', nome_da_coluna, flags=re.IGNORECASE)
			match_nbc   = re.search(r'NAT_BC_CRED', nome_da_coluna, flags=re.IGNORECASE)
			match_tipo  = re.search(r'TIPO_ITEM', nome_da_coluna, flags=re.IGNORECASE)
			match_mod   = re.search(r'COD_MOD', nome_da_coluna, flags=re.IGNORECASE)
			match_data  = re.search(r'^DT_|Data', nome_da_coluna, flags=re.IGNORECASE)
			match_chave = re.search(r'^CHV_|Chave Eletrônica', nome_da_coluna, flags=re.IGNORECASE)
			match_ncm   = re.search(r'COD_NCM', nome_da_coluna, flags=re.IGNORECASE)
			match_cnpj  = re.search(r'CNPJ', nome_da_coluna, flags=re.IGNORECASE)
			match_cpf   = re.search(r'CPF',  nome_da_coluna, flags=re.IGNORECASE)

			match_cst_contib = re.search(r'^CST_(PIS|COFINS)|CST_PIS_COFINS', nome_da_coluna, flags=re.IGNORECASE)
			match_cst_icms   = re.search(r'^CST_ICMS', nome_da_coluna, flags=re.IGNORECASE)

			# https://www.geeksforgeeks.org/switch-case-in-python-replacement/
			# Ao invés de usar vários 'if/elif/elif/elif/.../else', usar o dict switcher[chave] = valor, 
			# tal que switcher.get(True, 'default value') retorna o valor da última chave True.
			# bool(match_linha) retorna True ou False.
			switcher = {
				bool(match_linha):      self.formatar_linhas,
				bool(match_mes):        self.formatar_mes,
				bool(match_reg):        self.formatar_registro,
				bool(match_cfop):       self.formatar_cfop,
				bool(match_nbc):        self.formatar_nbc,
				bool(match_tipo):       self.formatar_tipo,
				bool(match_mod):        self.formatar_mod,
				bool(match_cst_contib): self.formatar_cst_contrib,
				bool(match_cst_icms):   self.formatar_cst_icms,
				bool(match_data):       CampoData.formatar,
				bool(match_chave):      CampoChaveEletronica.formatar,
				bool(match_ncm):        CampoNCM.formatar,
				bool(match_cnpj):       CampoCNPJ.formatar,
				bool(match_cpf):        CampoCPF.formatar,
				bool(match_cnpj and match_cpf): CampoCPFouCNPJ.formatar,
			}

			# Caso não ocorra nenhum match, retornar default value = self.funcao_identidade
			self.dicionario[nome_da_coluna] = switcher.get(True, self.funcao_identidade)

			#print(f'{switcher = } ; {nome_da_coluna = } ; {bool(match_data) = } ; {self.dicionario[nome_da_coluna] = } \n')
			#sleep(0.5)
		
		if self.verbose:
			for idx, key in enumerate(sorted(self.dicionario.keys()),1):
				print(f'{key:>40}: [{idx:>2}] {self.dicionario[key]}')
	
	def formatar_valores_das_colunas(self):

		for nome_da_coluna in self.lista_de_colunas:

			match_n_center = re.search(r'Linha|NUM_ITEM', nome_da_coluna, flags=re.IGNORECASE)
			match_n_right  = re.search(r'NUM_DOC', nome_da_coluna, flags=re.IGNORECASE)
			match_valor    = re.search(r'VL|Valor', nome_da_coluna, flags=re.IGNORECASE)
			match_aliquota = re.search(r'Aliq', nome_da_coluna, flags=re.IGNORECASE)
			match_data     = re.search(r'Data|DT_', nome_da_coluna, flags=re.IGNORECASE)

			self.dicionario[nome_da_coluna] = self.funcao_identidade
			
			# Estes vários if/elif/elif/... são executados apenas uma vez na execução do método/função.
			if match_n_center or match_n_right or match_valor or match_aliquota:
				self.dicionario[nome_da_coluna] = self.formatar_valores_reais
			elif match_data:
				self.dicionario[nome_da_coluna] = self.formatar_datas
	
	def formatar_colunas_do_arquivo_excel(self,workbook):

		format_default  = workbook.add_format()
		format_n_center = workbook.add_format({'num_format': '0', 'align':'center'})
		format_n_right  = workbook.add_format({'num_format': '0', 'align':'right'})
		format_valor    = workbook.add_format({'num_format': '#,##0.00', 'align':'right'})
		format_aliquota = workbook.add_format({'num_format': '#,##0.0000', 'align':'center'})
		format_data     = workbook.add_format({'num_format': 'dd/mm/yyyy', 'align':'center'})
		format_center   = workbook.add_format({'align':'center'})

		for nome_da_coluna in self.lista_de_colunas:

			match_n_center = re.search(r'Linha|NUM_ITEM', nome_da_coluna, flags=re.IGNORECASE)
			match_n_right  = re.search(r'NUM_DOC', nome_da_coluna, flags=re.IGNORECASE)
			match_valor    = re.search(r'VL|Valor', nome_da_coluna, flags=re.IGNORECASE)
			match_aliquota = re.search(r'Aliq', nome_da_coluna, flags=re.IGNORECASE)
			match_data     = re.search(r'Data|DT_', nome_da_coluna, flags=re.IGNORECASE)
			match_center   = re.search(r'Período|Operação', nome_da_coluna, flags=re.IGNORECASE)

			switcher = {
				bool(match_n_center):  format_n_center,
				bool(match_n_right):   format_n_right,
				bool(match_valor):     format_valor,
				bool(match_aliquota):  format_aliquota,
				bool(match_data):      format_data,
				bool(match_center):    format_center,
			}

			# Caso não ocorra nenhum match, retornar default value = format_default
			self.dicionario[nome_da_coluna] = switcher.get(True, format_default)


# Python OOP: Atributos e Métodos (def, funções)
class SPED_EFD_Info:
	"""
	Imprimir SPED EFD Contribuições ou ICMS_IPI nos formatos .csv e .xlsx tal que 
	contenha todas as informações suficientes para verificar a correção dos lançamentos 
	ou apuração das contribuições de PIS/COFINS ou do ICMS segundo a legislação vigente.
	"""
	
	# class or static variable
	
	# Python 3 Deep Dive (Part 4 - OOP)/03. Project 1/03. Project Solution - Transaction Numbers
	contador_de_linhas = itertools.count(2) # 2 é o valor inicial do contador
	
	### --- registros e colunas --- ###
	
	 # 'Data da Emissão do Documento Fiscal'
	registros_de_data_emissao  = ['DT_DOC', 'DT_DOC_INI', 'DT_REF_INI', 'DT_OPER']

	# 'Data da Entrada/Aquisição/Execução ou da Saída/Prestação/Conclusão'
	registros_de_data_execucao = ['DT_EXE_SERV', 'DT_E_S', 'DT_ENT', 'DT_A_P', 'DT_DOC_FIN', 'DT_REF_FIN']

	# merge/concatenating two lists in Python
	registros_de_data = ['DT_INI', 'DT_FIN'] + registros_de_data_emissao + registros_de_data_execucao 

	registros_de_identificacao_do_item = ['DESCR_ITEM', 'TIPO_ITEM', 'COD_NCM']

	registros_de_cadastro_do_participante = ['NOME_participante', 'CNPJ_participante', 'CPF_participante']

	registros_de_plano_de_contas = ['COD_NAT_CC', 'NOME_CTA']

	registros_de_codigo_cst = ['CST_PIS', 'CST_COFINS']

	registros_de_chave_eletronica = ['CHV_NFE', 'CHV_CTE', 'CHV_NFSE', 'CHV_DOCe', 'CHV_CFE', 'CHV_NFE_CTE']

	# adicionado 'VL_OPR' para EFD ICMS_IPI
	registros_de_valor = ['VL_DOC', 'VL_BRT', 'VL_OPER', 'VL_OPR', 'VL_OPER_DEP', 'VL_BC_CRED', 'VL_BC_EST', 
						  'VL_TOT_REC', 'VL_REC_CAIXA', 'VL_REC_COMP', 'VL_REC', 'VL_ITEM']

	# Imprimir as informações desta coluna, nesta ordem
	colunas_selecionadas = [
		'Linhas', 'Arquivo da SPED EFD', 'Nº da Linha da EFD', 'CNPJ', 'NOME', 'Mês do Período de Apuração', 
		'Ano do Período de Apuração', 'Tipo de Operação', 'IND_ORIG_CRED', 'REG', 'CST_PIS_COFINS', 
		'NAT_BC_CRED', 'CFOP', 'COD_PART', *registros_de_cadastro_do_participante, 'CNPJ_CPF_PART', 
		'Data de Emissão', 'Data de Execução', 'COD_ITEM', *registros_de_identificacao_do_item, 
		'Chave Eletrônica', 'COD_MOD', 'NUM_DOC', 'NUM_ITEM', 'COD_CTA', *registros_de_plano_de_contas, 
		'Valor do Item', 'VL_BC_PIS', 'VL_BC_COFINS', 'ALIQ_PIS', 'ALIQ_COFINS', 
		'VL_ISS', 'CST_ICMS', 'VL_BC_ICMS', 'ALIQ_ICMS'
	]
	
	# evitar duplicidade: Is there a more Pythonic way to prevent adding a duplicate to a list?
	registros_totais = set(
		registros_de_data + registros_de_identificacao_do_item + registros_de_plano_de_contas + 
		registros_de_codigo_cst + registros_de_chave_eletronica + registros_de_valor + 
		colunas_selecionadas)
	
	# initialize the attributes of the class
	
	def __init__(self, file_path=None, encoding=None, efd_tipo=None, verbose=False):

		if file_path is None or not os.path.isfile(file_path):
			raise ValueError(f'O arquivo file_path = {file_path} não é válido!')
		else:
			self.file_path = file_path
				
		if encoding is None:
			self.encoding = 'UTF-8'
		else:
			self.encoding = encoding

		if efd_tipo is None or re.search(r'PIS|COFINS|Contrib', efd_tipo, flags=re.IGNORECASE):
			self.objeto_sped = ArquivoDigital_PIS_COFINS() # instanciar objeto sped_efd
			self.efd_tipo = 'efd_contribuicoes'
		elif re.search(r'ICMS|IPI', efd_tipo, flags=re.IGNORECASE):
			self.objeto_sped = ArquivoDigital_ICMS_IPI()   # instanciar objeto sped_efd
			self.efd_tipo = 'efd_icms_ipi'
		else:
			raise ValueError(f'efd_tipo = {efd_tipo} inválido!')
		
		if not isinstance(verbose, bool):
			raise ValueError(f'verbose deve ser uma variável boolean (True or False). verbose = {verbose} é inválido!')
		else:
			self.verbose = verbose
		
		self.basename = os.path.basename(self.file_path)

		self.myDict = {}
	
	@property
	def imprimir_informacoes(self):

		select_object = My_Switch(type(self).registros_totais,verbose=self.verbose)
		select_object.formatar_colunas_do_arquivo_csv()
		self.myDict = select_object.dicionario
				
		self.objeto_sped.readfile(self.file_path, codificacao=self.encoding, verbose=self.verbose)
		
		self.info_do_participante = self.cadastro_do_participante(self.objeto_sped)
		
		if self.verbose:
			print(f'self.info_do_participante = {self.info_do_participante} ; len(self.info_do_participante) = {len(self.info_do_participante)}\n')
		
		self.info_do_item = self.identificacao_do_item(self.objeto_sped)

		if self.verbose:
			print(f'self.info_do_item = {self.info_do_item} ; len(self.info_do_item) = {len(self.info_do_item)}\n')
		
		self.info_da_conta = self.plano_de_contas_contabeis(self.objeto_sped)

		if self.verbose:
			print(f'self.info_da_conta = {self.info_da_conta} ; len(self.info_da_conta) = {len(self.info_da_conta)}\n')
		
		self.info_de_abertura = self.obter_info_de_abertura(self.objeto_sped)
		
		filename = os.path.splitext(self.file_path)[0] # ('./efd_info', '.py')
		arquivo_csv   = filename + '.csv'
		arquivo_excel = filename + '.xlsx'
		
		self.imprimir_informacoes_da_efd(self.objeto_sped, output_filename=arquivo_csv)

		self.convert_csv_to_xlsx(imput_csv=arquivo_csv, output_excel=arquivo_excel)

	def __repr__(self):
		# https://stackoverflow.com/questions/25577578/access-class-variable-from-instance
    	# Devo substituir 'self.__class__.static_var' por 'type(self).static_var' ?
		return f'{type(self).__name__}(file_path={self.file_path!r}, encoding={self.encoding!r}, efd_tipo={self.efd_tipo!r}, verbose={self.verbose!r})'

	def formatar_valor(self,nome,val):
		"""
		Evitar n repetições de 'if condicao_j then A_j else B_j' tal que 1 <= j <= n, 
		usar dicionário: myDict[key] = funtion_key(value)
		Better optimization technique using if/else or dictionary
		A series of if/else statement which receives the 'string' returns the appropriate function for it.
		A dictionary maintaining the key-value pair. key as strings, and values as the function objects, 
		and one main function to search and return the function object.
		"""
		# https://stackoverflow.com/questions/11445226/better-optimization-technique-using-if-else-or-dictionary
		# https://softwareengineering.stackexchange.com/questions/182093/why-store-a-function-inside-a-python-dictionary/182095
		# https://stackoverflow.com/questions/9168340/using-a-dictionary-to-select-function-to-execute
		try:
			# https://stackoverflow.com/questions/25577578/access-class-variable-from-instance
			# val_formated = self.__class__.myDict[nome](val)
			val_formated = self.myDict[nome](val)
		except:
			val_formated = val
		#print(f'nome = {nome} ; val = {val} ; val_formated = {val_formated}')
		return val_formated
		
	# https://radek.io/2011/07/21/static-variables-and-methods-in-python/
	@staticmethod
	def natureza_da_bc_dos_creditos(cfop):	
		"""
		http://sped.rfb.gov.br/arquivo/show/1681
		Tabela CFOP - Operações Geradoras de Créditos - Versão 1.0.0
		"""
		natureza_bc = None
		
		# Código 01 - CFOP de 'Aquisição de Bens para Revenda'
		if   cfop in ['1102','1113','1117','1118','1121','1251','1403','1652','2102','2113',
					  '2117','2118','2121','2251','2403','2652','3102','3251','3652']:
			natureza_bc = 1
		# Código 02 - CFOP de 'Aquisição de Bens Utilizados como Insumo'
		elif cfop in ['1101','1111','1116','1120','1122','1126','1128','1401','1407','1556',
					  '1651','1653','2101','2111','2116','2120','2122','2126','2128','2401',
					  '2407','2556','2651','2653','3101','3126','3128','3556','3651','3653']:
			natureza_bc = 2
		# Código 03 - CFOP de 'Aquisição de Serviços Utilizados como Insumos'
		elif cfop in ['1124','1125','1933','2124','2125','2933']:
			natureza_bc = 3
		# Código 12 - CFOP de 'Devolução de Vendas Sujeitas à Incidência Não-Cumulativa'
		elif cfop in ['1201','1202','1203','1204','1410','1411','1660','1661','1662','2201',
					  '2202','2410','2411','2660','2661','2662']:
			natureza_bc = 12
		# Código 13 - CFOP de 'Outras Operações com Direito a Crédito'
		elif cfop in ['1922','2922']:
			natureza_bc = 13
		
		return natureza_bc
	
	# https://stackoverflow.com/questions/25577578/access-class-variable-from-instance
	def cadastro_do_participante(self,sped_efd):
		"""
		Registro 0150: Tabela de Cadastro do Participante
		Retorno desta função:
		info_do_participante[codigo_do_participante][campo] = descricao
		"""
		blocoZero = sped_efd._blocos['0'] # Ler apenas o bloco 0.
		info = {}
		for registro in blocoZero.registros:
			REG = registro.valores[1]
			if REG != '0150':
				continue
			codigo_do_participante = None
			for campo in registro.campos:
				valor = registro.valores[campo.indice]
				# Fazer distinção entre 'NOME' do Registro0000 e 'NOME' do Registro0150
				nome  = campo.nome + '_participante'
				if campo.nome == 'COD_PART':
					codigo_do_participante = valor
					info[codigo_do_participante] = {}
				if nome in type(self).registros_de_cadastro_do_participante and codigo_do_participante is not None:
					info[codigo_do_participante][nome] = valor
		return info

	def identificacao_do_item(self,sped_efd):
		"""
		Registro 0200: Tabela de Identificação do Item (Produtos e Serviços)
		Retorno desta função:
		info_do_item[codigo_do_item][campo] = descricao
		"""
		blocoZero = sped_efd._blocos['0'] # Ler apenas o bloco 0.
		info = {}
		for registro in blocoZero.registros:
			REG = registro.valores[1]
			if REG != '0200':
				continue
			codigo_do_item = None
			for campo in registro.campos:
				valor = registro.valores[campo.indice]
				if campo.nome == 'COD_ITEM':
					codigo_do_item = valor
					info[codigo_do_item] = {}
				if campo.nome in type(self).registros_de_identificacao_do_item and codigo_do_item is not None:
					info[codigo_do_item][campo.nome] = valor
		return info

	def plano_de_contas_contabeis(self,sped_efd):
		"""
		Registro 0500: Plano de Contas Contábeis
		Retorno desta função:
		info_do_item[codigo_do_item][campo] = descricao
		"""
		blocoZero = sped_efd._blocos['0'] # Ler apenas o bloco 0.
		info = {}
		for registro in blocoZero.registros:
			REG = registro.valores[1]
			if REG != '0500':
				continue
			codigo_do_item = None
			for campo in registro.campos:
				valor = registro.valores[campo.indice]
				if campo.nome == 'COD_CTA':
					codigo_do_item = valor
					info[codigo_do_item] = {}
			for campo in registro.campos:
				valor = registro.valores[campo.indice]
				if campo.nome in type(self).registros_de_plano_de_contas and codigo_do_item is not None:
					info[codigo_do_item][campo.nome] = valor
		return info


	def obter_info_de_abertura(self,sped_efd):
		registro = sped_efd._registro_abertura
		REG = registro.valores[1]
		nivel = registro.nivel

		# Utilizar uma combinação de valores para identificar univocamente um item.
		combinacao = 'registro de abertura'
		
		info_de_abertura = {}
		
		# https://www.geeksforgeeks.org/python-creating-multidimensional-dictionary/
		info_de_abertura.setdefault(nivel, {}).setdefault(combinacao, {})['Nível Hierárquico'] = nivel
		
		if self.verbose:
			print(f'registro.as_line() = {registro.as_line()} ; REG = {REG} ; nivel = {nivel}')
			print(f'info_de_abertura = {info_de_abertura}\n')
		
		for campo in registro.campos:
			
			valor = registro.valores[campo.indice]
			
			if campo.nome in type(self).colunas_selecionadas:
				info_de_abertura[nivel][combinacao][campo.nome] = valor	
			if campo.nome == 'DT_INI':
					ddmmaaaa = registro.valores[campo.indice]
					info_de_abertura[nivel][combinacao]['Data de Emissão'] = valor
					info_de_abertura[nivel][combinacao]['Mês do Período de Apuração'] = ddmmaaaa[2:4]
					info_de_abertura[nivel][combinacao]['Ano do Período de Apuração'] = ddmmaaaa[4:8]
			if campo.nome == 'DT_FIN':
					info_de_abertura[nivel][combinacao]['Data de Execução'] = valor
			if self.verbose:
				valor_formatado = self.formatar_valor(nome=campo.nome, val=valor)
				print(f'campo.indice = {campo.indice:>2} ; campo.nome = {campo.nome:>22} ; registro.valores[{campo.indice:>2}] = {valor:<50} ; valor_formatado = {valor_formatado}')		

		if self.verbose:
			print(f'\ninfo_de_abertura = {info_de_abertura}\n')
		
		return info_de_abertura
	
	def adicionar_informacoes(self,dict_info):
		"""
		Adicionar informações em dict_info
		Formatar alguns de seus campos com o uso de tabelas ou funções
		"""
		dict_info['Arquivo da SPED EFD'] = self.basename
		dict_info['Linhas'] = next(type(self).contador_de_linhas)

		# re.search: find something anywhere in the string and return a match object.
		if 'CST_PIS_COFINS' in dict_info and re.search(r'\d{1,2}', dict_info['CST_PIS_COFINS']):
			cst = int(dict_info['CST_PIS_COFINS'])
			if 1 <= cst <= 49:
				dict_info['Tipo de Operação'] = 'Saída'
			elif 50 <= cst <= 99:
				dict_info['Tipo de Operação'] = 'Entrada'
		
		# adicionar informação de NAT_BC_CRED para os créditos (50 <= cst <= 66) 
		# quando houver informação do CFOP e NAT_BC_CRED estiver vazio.
		if ('CFOP' in dict_info and 'NAT_BC_CRED' in dict_info 
			and re.search(r'\d{4}', dict_info['CFOP']) and len(dict_info['NAT_BC_CRED']) == 0
			#and ( re.search(r'[1-9]', dict_info['ALIQ_PIS']) or re.search(r'[1-9]', dict_info['ALIQ_COFINS']) ) # aliq_cofins > 0
			and 'CST_PIS_COFINS' in dict_info and re.search(r'\d{1,2}', dict_info['CST_PIS_COFINS'])):
			cfop = str(dict_info['CFOP'])
			cst  = int(dict_info['CST_PIS_COFINS'])
			if 50 <= cst <= 66:
				dict_info['NAT_BC_CRED'] = type(self).natureza_da_bc_dos_creditos(cfop)
		
		# Índice de Origem do Crédito: Leia os comentários do 'Registro M100: Crédito de PIS/Pasep Relativo ao Período'.
		# Os códigos vinculados à importação (108, 208 e 308) são obtidos através da informação de CFOP 
		# iniciado em 3 (quando existente) ou pelo campo IND_ORIG_CRED nos demais casos.
		indicador_de_origem = 'Mercado Interno' # Default Value: 0 - Mercado Interno ; 1 - Mercado Externo (Importação).
		if (('CFOP' in dict_info and re.search(r'^3\d{3}', dict_info['CFOP'])) or
			('IND_ORIG_CRED' in dict_info and dict_info['IND_ORIG_CRED'] == '1')):
			indicador_de_origem = 'Mercado Externo (Importação)'
		dict_info['IND_ORIG_CRED'] = indicador_de_origem

		# adicionar informação de cadastro do participante obtido do Registro 0150
		# info_do_participante[codigo_do_participante][campo] = descricao
		if 'COD_PART' in dict_info and dict_info['COD_PART'] in self.info_do_participante:
			codigo_do_participante = dict_info['COD_PART']
			for campo in self.info_do_participante[codigo_do_participante]:
				dict_info[campo] = self.info_do_participante[codigo_do_participante][campo]

		# adicionar informação de identificação do item obtido do Registro 0200
		# info_do_item[codigo_do_item][campo] = descricao
		if 'COD_ITEM' in dict_info and dict_info['COD_ITEM'] in self.info_do_item:
			codigo_do_item = dict_info['COD_ITEM']
			for campo in self.info_do_item[codigo_do_item]:
				dict_info[campo] = self.info_do_item[codigo_do_item][campo]
		
		# adicionar informação do plano de contas obtido do Registro 0500
		# info_da_conta[codigo_da_conta][campo] = descricao
		if 'COD_CTA' in dict_info and dict_info['COD_CTA'] in self.info_da_conta:
			codigo_da_conta = dict_info['COD_CTA']
			for campo in self.info_da_conta[codigo_da_conta]:
				val = str(self.info_da_conta[codigo_da_conta][campo])
				if campo == 'COD_NAT_CC' and re.search(r'\d{1,2}', val):
					val = val.zfill(2) # val = f'{int(val):02d}'
					val = val + ' - ' + EFD_Tabelas.tabela_natureza_da_conta[val]
				dict_info[campo] = val
		
		# Ao final, formatar alguns valores dos campos
		for campo in dict_info.copy():
			valor_formatado  = self.formatar_valor(nome=campo, val=dict_info[campo])
			dict_info[campo] = valor_formatado
		
		return dict_info
	
	def imprimir_informacoes_da_efd(self,sped_efd,output_filename):
		
		my_regex = r'^[A-K]' # Ler os blocos da A a K.
		
		campos_necessarios = ['CST_PIS', 'CST_COFINS', 'VL_BC_PIS', 'VL_BC_COFINS']
		# Bastam os seguintes campos, desde que os registros de PIS/PASEP ocorram sempre anteriores aos registros de COFINS:
		# campos_necessarios = ['CST_COFINS', 'VL_BC_COFINS']

		if self.efd_tipo == 'efd_icms_ipi':
			campos_necessarios = ['CST_ICMS', 'VL_BC_ICMS']
		
		# https://docs.python.org/3/library/csv.html
		with open(output_filename, 'w', newline='', encoding='utf-8', errors='ignore') as csvfile:

			writer = csv.writer(csvfile, delimiter=';')
			writer.writerow(type(self).colunas_selecionadas) # imprimir nomes das colunas apenas uma vez
			
			for key in sped_efd._blocos.keys():
				
				match_bloco = re.search(my_regex, key, flags=re.IGNORECASE)
				if not match_bloco:
					continue
				
				bloco = sped_efd._blocos[key]
				count = 1
				
				info = self.info_de_abertura
				
				for registro in bloco.registros:
					
					REG = registro.valores[1]
					
					try:
						nivel_anterior = nivel
						num_de_campos_anterior = num_de_campos
					except:
						nivel_anterior = registro.nivel + 1
						num_de_campos_anterior = len(registro.campos) + 1
					
					nivel = registro.nivel # nível atual
					num_de_campos = len(registro.campos)

					cst_pis = ''      # 2 caracteres
					cst_cofins = ''   # 2 caracteres
					cst_icms = ''     # 3 caracteres
					cfop = 'cfop'     # 4 caracteres
					valor_item = 'valor_item'
					
					for campo in registro.campos:
						if campo.nome == 'CST_PIS': 
							cst_pis = registro.valores[campo.indice]
						if campo.nome == 'CST_COFINS': 
							cst_cofins = registro.valores[campo.indice]
						if campo.nome == 'CST_ICMS': 
							cst_icms = registro.valores[campo.indice]
						if campo.nome == 'CFOP': 
							cfop = registro.valores[campo.indice]
						if campo.nome in type(self).registros_de_valor: 
							valor_item = registro.valores[campo.indice]
					
					cst_contribuicao = max(cst_pis,cst_cofins)

					# Utilizar uma combinação de valores para identificar univocamente um item.
					combinacao = f'{cst_contribuicao}_{cst_icms}_{cfop}_{valor_item}'
					
					if self.verbose:
						print(f'\ncount = {count:>2} ; key = {key} ; REG = {REG} ; nivel_anterior = {nivel_anterior} ; nivel = {nivel} ; ', end='')
						print(f'num_de_campos_anterior = {num_de_campos_anterior} ; num_de_campos = {num_de_campos} ; ', end='')
						print(f'cst_pis = {cst_pis} ; cst_cofins = {cst_cofins} ; cst_contribuicao = {cst_contribuicao}')
						print(f'registro.as_line() = {registro.as_line()}')

					# As informações do pai e respectivos filhos devem ser apagadas quando 
					# o nivel hierárquico regride dos filhos para pais diferentes.
					if nivel < nivel_anterior or (nivel == nivel_anterior and num_de_campos < num_de_campos_anterior):
						if self.verbose:
							if nivel < nivel_anterior:
								print(f'\n nivel atual: nivel = {nivel} < nivel_anterior = {nivel_anterior} ; ', end='')
							if nivel == nivel_anterior and num_de_campos < num_de_campos_anterior:
								print(f'\n numero de campos atual: num_de_campos = {num_de_campos} < num_de_campos_anterior = {num_de_campos_anterior} ; ', end='')
							print(f'deletar informações em info a partir do nível {nivel} em diante:')
						
						# Delete items from dictionary while iterating: 
						# https://www.geeksforgeeks.org/python-delete-items-from-dictionary-while-iterating/
						for nv in list(info):
							if nv >= nivel:
								del info[nv]
								if self.verbose:
									print(f'\t *** deletar informações do nível {nv}: del info[{nv}] ***')
						print() if self.verbose else 0
					
					# https://www.geeksforgeeks.org/python-creating-multidimensional-dictionary/
					info.setdefault(nivel, {}).setdefault(combinacao, {})['Nível Hierárquico'] = nivel
					info[nivel][combinacao]['Valor do Item'] = valor_item
					info[nivel][combinacao]['CST_PIS_COFINS'] = cst_contribuicao
					
					for campo in registro.campos:
						
						try:
							valor = registro.valores[campo.indice]
						except:
							valor = f'{REG}[{campo.indice}:{campo.nome}] sem valor definido'
						
						if self.verbose:
							valor_formatado = self.formatar_valor(nome=campo.nome, val=valor)
							print(f'campo.indice = {campo.indice:>2} ; campo.nome = {campo.nome:>22} ; registro.valores[{campo.indice:>2}] = {valor:<50} ; valor_formatado = {valor_formatado}')
						
						if campo.nome not in type(self).registros_totais: # filtrar registros_totais
							continue
						
						# reter em info{} as informações dos registros contidos em registros_totais
						info[nivel][combinacao][campo.nome] = valor
						
						# Informar os campos em registros_de_data_emissao na coluna 'Data de Emissão'.
						if campo.nome in type(self).registros_de_data_emissao:
							info[nivel][combinacao]['Data de Emissão'] = valor
						# Informar os campos em registros_de_data_execucao na coluna 'Data de Execução'.
						if campo.nome in type(self).registros_de_data_execucao:
							info[nivel][combinacao]['Data de Execução'] = valor
						# Informar os campos de chave eletrônica de 44 dígitos na coluna 'Chave Eletrônica'.
						if campo.nome in type(self).registros_de_chave_eletronica:
							info[nivel][combinacao]['Chave Eletrônica'] = valor

					if self.verbose:
						print(f'\n-->info[nivel][combinacao] = info[{nivel}][{combinacao}] = {info[nivel][combinacao]}\n')
					
					#https://stackoverflow.com/questions/3931541/how-to-check-if-all-of-the-following-items-are-in-a-list
					# set(['a', 'c']).issubset(['a', 'b', 'c', 'd']) or set(lista1).issubset(lista2)

					if set(campos_necessarios).issubset( info[nivel][combinacao] ):
						
						# import this: Zen of Python: Flat is better than nested.
						flattened_info = {} # eliminar os dois niveis [nivel][combinacao] e trazer todas as informações para apenas uma dimensão.
						seen_column = set() # evitar duplicidade: Is there a more Pythonic way to prevent adding a duplicate to a list?

						# em info{} há os registros_totais, em flattened_info{} apenas as colunas para impressao
						for coluna in type(self).colunas_selecionadas:
							flattened_info[coluna] = '' # atribuir valor inicial para todas as colunas
							
							if coluna in info[nivel][combinacao]:
								flattened_info[coluna] = info[nivel][combinacao][coluna] # eliminar os dois niveis [nivel][combinacao]
								seen_column.add(coluna)
								if self.verbose:
									print(f'nivel = {nivel:<10} ; combinacao = {combinacao:25} ; coluna = {coluna:>35} = {info[nivel][combinacao][coluna]:<35} ; info[nivel][combinacao] = {info[nivel][combinacao]}')
								continue

							for nv in sorted(info,reverse=True): # nível em ordem decrescente
								if coluna in seen_column:        # informações já obtidas
									break                        # as informações obtidas do nível mais alto prevalecerá
								for comb in info[nv]:
									if coluna in info[nv][comb]:
										flattened_info[coluna] = info[nv][comb][coluna] # eliminar os dois niveis [nivel][combinacao]
										seen_column.add(coluna)
										if self.verbose:
											print(f'nivel = {nivel} ; nv = {nv} ; combinacao = {comb:25} ; coluna = {coluna:>35} = {info[nv][comb][coluna]:<35} ; info[nivel][combinacao] = {info[nv][comb]}')
						
						print() if self.verbose else 0
						
						flattened_info['Nº da Linha da EFD'] = registro.numero_da_linha
						
						# Adicionar informações em flattened_info ou formatar alguns de seus campos com o uso de tabelas ou funções
						flattened_info = self.adicionar_informacoes(flattened_info)
						
						writer.writerow( flattened_info.values() )
					
					# Se verbose == True, limitar tamanho do arquivo impresso
					# Imprimir apenas os 20 primeiros registros de cada Bloco
					count += 1
					if self.verbose and count > 20:
						break
		
		print(f"Gerado o arquivo csv: '{output_filename}'.")


	def convert_csv_to_xlsx(self, imput_csv, output_excel):

		# Create an new Excel file and add a worksheet.
		workbook = xlsxwriter.Workbook(output_excel)
		worksheet = workbook.add_worksheet('Itens de Docs Fiscais')
		workbook.set_properties({'comments': 'Created with Python and XlsxWriter'})
		
		# definindo a altura da primeira coluna, row_index == 0
		worksheet.set_row(0, 30)

		# Freeze pane on the top row.
		worksheet.freeze_panes(1, 0)

		# Set up some formatting
		header_format = workbook.add_format({
						'align':'center', 'valign':'vcenter', 
						'bg_color':'#C5D9F1', 'text_wrap':True, 
						'font_size':10})
		
		select_value = My_Switch(type(self).registros_totais,verbose=self.verbose)
		select_value.formatar_valores_das_colunas()
		myValue = select_value.dicionario

		select_format = My_Switch(type(self).registros_totais,verbose=self.verbose)
		select_format.formatar_colunas_do_arquivo_excel(workbook)
		myFormat = select_format.dicionario

		# First we find the length of the header column 
		largura_max = [len(c) for c in type(self).colunas_selecionadas]
        
		with open(imput_csv, 'r', encoding='utf-8', errors='ignore') as file:
        
			reader = csv.reader(file, delimiter=';')
			for row_index, row in enumerate(reader):

				# nomes das colunas
				if row_index == 0:
					worksheet.write_row(row_index, 0, tuple(type(self).colunas_selecionadas), header_format)
					continue

				for column_index, cell in enumerate(row):

					# reter largura máxima
					if len(cell) > largura_max[column_index]:
						largura_max[column_index] = len(cell)
					
					column_name = type(self).colunas_selecionadas[column_index]

					if len(cell) > 0:
						worksheet.write(row_index, column_index, myValue[column_name](cell), myFormat[column_name])
					else:
						# Write cell with row/column notation.
						worksheet.write(row_index, column_index, cell)
		
		# Ajustar largura das colunas com os valores máximos
		largura_min = 4
		for i, width in enumerate(largura_max):
			if width > 120: # largura máxima
				width = 120
			worksheet.set_column(i, i, width + largura_min)
		
		# Set the autofilter( $first_row, $first_col, $last_row, $last_col )
		worksheet.autofilter(0, 0, 0, len(largura_max) - 1)

		workbook.close()

		print(f"Gerado o arquivo XLSX Excel: '{output_excel}'.")