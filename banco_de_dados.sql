-- ============================================================
-- CardioLab - Banco de Dados MySQL
-- Plataforma de Cardiologia
-- ============================================================

CREATE DATABASE IF NOT EXISTS cardiolab
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE cardiolab;

-- ============================================================
-- TABELA: usuarios
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    cpf VARCHAR(14) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    foto_perfil VARCHAR(500),
    perfil ENUM('paciente', 'medico', 'administrador') NOT NULL DEFAULT 'paciente',
    dois_fatores_ativo TINYINT(1) DEFAULT 0,
    consentimento_aceito TINYINT(1) DEFAULT 0,
    ativo TINYINT(1) DEFAULT 1,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usuarios_email (email),
    INDEX idx_usuarios_cpf (cpf),
    INDEX idx_usuarios_perfil (perfil)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: pacientes
-- ============================================================
CREATE TABLE IF NOT EXISTS pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL UNIQUE,
    data_nascimento DATE,
    telefone VARCHAR(20),
    cep VARCHAR(10),
    endereco VARCHAR(300),
    cartao_sus VARCHAR(20),
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_pacientes_usuario (usuario_id)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: planos_carteirinha
-- Convênio interno / carteirinha CardioLab Care.
-- ============================================================
CREATE TABLE IF NOT EXISTS planos_carteirinha (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(40) NOT NULL UNIQUE,
    nome VARCHAR(120) NOT NULL,
    valor_mensal DECIMAL(10,2) NOT NULL DEFAULT 0,
    desconto_consulta_percentual DECIMAL(5,2) NOT NULL DEFAULT 0,
    desconto_exame_percentual DECIMAL(5,2) NOT NULL DEFAULT 0,
    encaixes_urgentes_mes INT NOT NULL DEFAULT 0,
    teleconsultas_mes INT NOT NULL DEFAULT 0,
    descricao TEXT,
    beneficios_json TEXT,
    ativo TINYINT(1) DEFAULT 1,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_planos_carteirinha_codigo (codigo),
    INDEX idx_planos_carteirinha_ativo (ativo)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: carteirinhas_pacientes
-- Vincula paciente, plano, numero da carteirinha, validade e situacao.
-- ============================================================
CREATE TABLE IF NOT EXISTS carteirinhas_pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    plano_id INT NOT NULL,
    numero_carteirinha VARCHAR(40) NOT NULL UNIQUE,
    titular VARCHAR(200),
    situacao ENUM('em_analise','ativa','expirada','cancelada') NOT NULL DEFAULT 'em_analise',
    inicio_em DATE,
    expira_em DATE,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    FOREIGN KEY (plano_id) REFERENCES planos_carteirinha(id) ON DELETE RESTRICT,
    INDEX idx_carteirinhas_paciente (paciente_id),
    INDEX idx_carteirinhas_situacao (situacao),
    INDEX idx_carteirinhas_numero (numero_carteirinha)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: medicos
-- ============================================================
CREATE TABLE IF NOT EXISTS medicos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL UNIQUE,
    especialidade VARCHAR(100) NOT NULL,
    crm VARCHAR(20) NOT NULL,
    rqe VARCHAR(20),
    biografia TEXT,
    expediente_inicio TIME DEFAULT '08:00:00',
    expediente_fim TIME DEFAULT '18:00:00',
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_medicos_usuario (usuario_id)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: servicos
-- ============================================================
CREATE TABLE IF NOT EXISTS servicos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    descricao TEXT,
    preparo TEXT,
    duracao_minutos INT DEFAULT 30,
    indicacao TEXT
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: consultas
-- ============================================================
CREATE TABLE IF NOT EXISTS consultas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    medico_id INT NOT NULL,
    servico_id INT NOT NULL,
    data_consulta DATE NOT NULL,
    horario_consulta TIME NOT NULL,
    duracao_minutos INT DEFAULT 30,
    situacao ENUM('agendada','confirmada','em_atendimento','finalizada','cancelada','faltou') DEFAULT 'agendada',
    confirmada_em DATETIME,
    posicao_fila INT,
    sala_teleconsulta_url VARCHAR(500),
    motivo_cancelamento TEXT,
    lembrete_24h_enviado TINYINT(1) DEFAULT 0,
    lembrete_2h_enviado TINYINT(1) DEFAULT 0,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    FOREIGN KEY (medico_id) REFERENCES medicos(id) ON DELETE CASCADE,
    FOREIGN KEY (servico_id) REFERENCES servicos(id) ON DELETE CASCADE,
    -- Conflitos sao validados por sobreposicao de duracao na aplicacao.
    INDEX idx_consultas_medico_data_hora (medico_id, data_consulta, horario_consulta),
    INDEX idx_consultas_data (data_consulta),
    INDEX idx_consultas_paciente (paciente_id),
    INDEX idx_consultas_medico (medico_id),
    INDEX idx_consultas_situacao (situacao)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: resultados_exames
-- ============================================================
CREATE TABLE IF NOT EXISTS resultados_exames (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    medico_id INT,
    servico_id INT,
    titulo VARCHAR(200) NOT NULL,
    arquivo_url VARCHAR(500),
    tipo_resultado ENUM('pdf','imagem','dicom','texto') DEFAULT 'pdf',
    assinatura_digital VARCHAR(300),
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    FOREIGN KEY (medico_id) REFERENCES medicos(id) ON DELETE SET NULL,
    FOREIGN KEY (servico_id) REFERENCES servicos(id) ON DELETE SET NULL,
    INDEX idx_resultados_exames_paciente (paciente_id)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: metricas_saude
-- ============================================================
CREATE TABLE IF NOT EXISTS metricas_saude (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    pressao_arterial VARCHAR(20),
    frequencia_cardiaca INT,
    peso DECIMAL(5,2),
    imc DECIMAL(4,2),
    glicemia DECIMAL(6,2),
    colesterol DECIMAL(6,2),
    medido_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    INDEX idx_metricas_paciente (paciente_id),
    INDEX idx_metricas_data (medido_em)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: prontuarios
-- ============================================================
CREATE TABLE IF NOT EXISTS prontuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    medico_id INT NOT NULL,
    observacoes TEXT,
    medicamentos TEXT,
    alerta_risco VARCHAR(100),
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    FOREIGN KEY (medico_id) REFERENCES medicos(id) ON DELETE CASCADE,
    INDEX idx_prontuarios_paciente (paciente_id)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: notificacoes
-- ============================================================
CREATE TABLE IF NOT EXISTS notificacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    mensagem TEXT,
    tipo ENUM('informacao','sucesso','atencao','perigo','lembrete') DEFAULT 'informacao',
    lida TINYINT(1) DEFAULT 0,
    lida_em DATETIME,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_notificacoes_usuario (usuario_id),
    INDEX idx_notificacoes_lida (lida)
) ENGINE=InnoDB;



-- ============================================================
-- TABELA: auditoria
-- ============================================================
CREATE TABLE IF NOT EXISTS auditoria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT,
    acao VARCHAR(200) NOT NULL,
    endereco_ip VARCHAR(45),
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_auditoria_usuario (usuario_id),
    INDEX idx_auditoria_data (criado_em)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: artigos
-- ============================================================
CREATE TABLE IF NOT EXISTS artigos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(300) NOT NULL,
    categoria VARCHAR(100),
    conteudo TEXT NOT NULL,
    imagem_url VARCHAR(500),
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_artigos_categoria (categoria)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: avaliacoes
-- Unifica depoimentos publicos e respostas NPS em uma unica tabela.
-- tipo = 'depoimento' para avaliacoes exibidas na home (escala 0-10).
-- tipo = 'nps' para pesquisa Net Promoter Score (escala 0-10).
-- ============================================================
CREATE TABLE IF NOT EXISTS avaliacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT,
    nome_paciente VARCHAR(200),
    tipo ENUM('depoimento', 'nps') NOT NULL DEFAULT 'depoimento',
    nota INT CHECK (nota >= 0 AND nota <= 10),
    comentario TEXT,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE SET NULL,
    INDEX idx_avaliacoes_tipo (tipo)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: solicitacoes_senha
-- ============================================================
CREATE TABLE IF NOT EXISTS solicitacoes_senha (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    identificador VARCHAR(200) NOT NULL,
    situacao ENUM('pendente','concluida','cancelada') NOT NULL DEFAULT 'pendente',
    ip_solicitante VARCHAR(45),
    resolvido_por INT,
    resolvido_em DATETIME,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (resolvido_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_solicitacoes_senha_usuario (usuario_id),
    INDEX idx_solicitacoes_senha_status (situacao),
    INDEX idx_solicitacoes_senha_criada (criado_em)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: calculos_risco
-- ============================================================
CREATE TABLE IF NOT EXISTS calculos_risco (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    sexo ENUM('M','F') NOT NULL,
    idade INT NOT NULL,
    colesterol_total DECIMAL(6,2) NOT NULL,
    hdl DECIMAL(6,2) NOT NULL,
    pressao_sistolica DECIMAL(6,2) NOT NULL,
    trata_pressao TINYINT(1) DEFAULT 0,
    fumante TINYINT(1) DEFAULT 0,
    diabetes TINYINT(1) DEFAULT 0,
    risco_percentual DECIMAL(5,2) NOT NULL,
    classe_risco VARCHAR(30) NOT NULL,
    recomendacoes_json JSON,
    calculado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    INDEX idx_calculos_risco_paciente (paciente_id),
    INDEX idx_calculos_risco_classe (classe_risco)
) ENGINE=InnoDB;



-- ============================================================
-- TABELA: lista_espera
-- ============================================================
CREATE TABLE IF NOT EXISTS lista_espera (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    medico_id INT NOT NULL,
    servico_id INT NOT NULL,
    data_desejada DATE,
    horario_desejado TIME,
    situacao ENUM('aguardando','notificado','convertido','cancelado') DEFAULT 'aguardando',
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    FOREIGN KEY (medico_id) REFERENCES medicos(id) ON DELETE CASCADE,
    FOREIGN KEY (servico_id) REFERENCES servicos(id) ON DELETE CASCADE,
    INDEX idx_lista_espera_busca (medico_id, servico_id, data_desejada, situacao)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: tokens_compartilhamento_exames
-- ============================================================
CREATE TABLE IF NOT EXISTS tokens_compartilhamento_exames (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exame_id INT NOT NULL,
    token CHAR(32) NOT NULL UNIQUE,
    expira_em DATETIME NOT NULL,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exame_id) REFERENCES resultados_exames(id) ON DELETE CASCADE,
    INDEX idx_tokens_exames_token (token),
    INDEX idx_tokens_exames_expiracao (expira_em)
) ENGINE=InnoDB;

-- ============================================================
-- TABELA: configuracoes_clinica
-- ============================================================
CREATE TABLE IF NOT EXISTS configuracoes_clinica (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- ============================================================
-- SEED DATA - Dados Iniciais
-- ============================================================

-- Senhas: todas são "cardiolab123" com hash werkzeug
-- Hash gerado com: generate_password_hash('cardiolab123', method='pbkdf2:sha256')
-- O hash abaixo é válido para werkzeug

-- Admin
INSERT INTO usuarios (nome, email, cpf, senha_hash, perfil, dois_fatores_ativo) VALUES
('Administrador CardioLab', 'admin@cardiolab.com.br', '935.411.347-80', 
 'pbkdf2:sha256:600000$r8WlNF8qAXg8bkka$0566f6cb091bf951919dd41885bd0d19dab9ccff2edbfec21b1ab651fe8d8211', 
 'administrador', 0);

-- Médico cardiologista
INSERT INTO usuarios (nome, email, cpf, senha_hash, perfil, dois_fatores_ativo) VALUES
('Dr. Ricardo Mendes', 'dr.ricardo@cardiolab.com.br', '706.785.420-23',
 'pbkdf2:sha256:600000$r8WlNF8qAXg8bkka$0566f6cb091bf951919dd41885bd0d19dab9ccff2edbfec21b1ab651fe8d8211',
 'medico', 0);

-- Paciente
INSERT INTO usuarios (nome, email, cpf, senha_hash, perfil, dois_fatores_ativo) VALUES
('Maria Silva Santos', 'maria@email.com', '481.672.930-50',
 'pbkdf2:sha256:600000$r8WlNF8qAXg8bkka$0566f6cb091bf951919dd41885bd0d19dab9ccff2edbfec21b1ab651fe8d8211',
 'paciente', 0);

-- Perfis ficticios adicionais para demonstracao
INSERT INTO usuarios (nome, email, cpf, senha_hash, perfil, dois_fatores_ativo) VALUES
('Dra. Helena Costa', 'dra.helena@cardiolab.com.br', '371.946.280-31',
 'pbkdf2:sha256:600000$r8WlNF8qAXg8bkka$0566f6cb091bf951919dd41885bd0d19dab9ccff2edbfec21b1ab651fe8d8211',
 'medico', 0),
('Dr. Bruno Almeida', 'dr.bruno@cardiolab.com.br', '682.407.195-11',
 'pbkdf2:sha256:600000$r8WlNF8qAXg8bkka$0566f6cb091bf951919dd41885bd0d19dab9ccff2edbfec21b1ab651fe8d8211',
 'medico', 0),
('Dra. Camila Torres', 'dra.camila@cardiolab.com.br', '519.283.746-46',
 'pbkdf2:sha256:600000$r8WlNF8qAXg8bkka$0566f6cb091bf951919dd41885bd0d19dab9ccff2edbfec21b1ab651fe8d8211',
 'medico', 0),
('Paulo Henrique Lima', 'paulo@email.com', '804.617.239-13',
 'pbkdf2:sha256:600000$r8WlNF8qAXg8bkka$0566f6cb091bf951919dd41885bd0d19dab9ccff2edbfec21b1ab651fe8d8211',
 'paciente', 0),
('Luciana Araujo Martins', 'luciana@email.com', '260.439.718-87',
 'pbkdf2:sha256:600000$r8WlNF8qAXg8bkka$0566f6cb091bf951919dd41885bd0d19dab9ccff2edbfec21b1ab651fe8d8211',
 'paciente', 0),
('Marcos Vieira Rocha', 'marcos@email.com', '740.285.193-14',
 'pbkdf2:sha256:600000$r8WlNF8qAXg8bkka$0566f6cb091bf951919dd41885bd0d19dab9ccff2edbfec21b1ab651fe8d8211',
 'paciente', 0),
('Renata Figueiredo Nunes', 'renata@email.com', '398.562.041-51',
 'pbkdf2:sha256:600000$r8WlNF8qAXg8bkka$0566f6cb091bf951919dd41885bd0d19dab9ccff2edbfec21b1ab651fe8d8211',
 'paciente', 0);

UPDATE usuarios SET foto_perfil = '/static/assets/medicos/ricardo-souza.jpg' WHERE email = 'dr.ricardo@cardiolab.com.br';
UPDATE usuarios SET foto_perfil = '/static/assets/medicos/helena-costa.jpg' WHERE email = 'dra.helena@cardiolab.com.br';
UPDATE usuarios SET foto_perfil = '/static/assets/medicos/bruno-almeida.jpg' WHERE email = 'dr.bruno@cardiolab.com.br';
UPDATE usuarios SET foto_perfil = '/static/assets/medicos/camila-torres.jpg' WHERE email = 'dra.camila@cardiolab.com.br';
UPDATE usuarios SET foto_perfil = '/static/assets/avatars/paciente-1.svg' WHERE email = 'maria@email.com';
UPDATE usuarios SET foto_perfil = '/static/assets/avatars/paciente-2.svg' WHERE email = 'paulo@email.com';
UPDATE usuarios SET foto_perfil = '/static/assets/avatars/paciente-3.svg' WHERE email = 'luciana@email.com';
UPDATE usuarios SET foto_perfil = '/static/assets/avatars/paciente-4.svg' WHERE email = 'marcos@email.com';
UPDATE usuarios SET foto_perfil = '/static/assets/avatars/paciente-5.svg' WHERE email = 'renata@email.com';

-- Dados do paciente
INSERT INTO pacientes (usuario_id, data_nascimento, telefone, cep, endereco, cartao_sus) VALUES
(3, '1958-03-15', '(11) 98765-4321', '01001-000', 'Rua das Flores, 123 - São Paulo/SP', '123456789012345');

INSERT INTO pacientes (usuario_id, data_nascimento, telefone, cep, endereco, cartao_sus) VALUES
(7, '1974-08-22', '(11) 97654-2100', '01310-100', 'Av. Paulista, 900 - Sao Paulo/SP', '223456789012345'),
(8, '1986-11-05', '(11) 96543-2100', '04004-030', 'Rua Vergueiro, 455 - Sao Paulo/SP', '323456789012345'),
(9, '1969-02-18', '(11) 95432-2100', '05005-060', 'Rua Cardoso de Almeida, 80 - Sao Paulo/SP', '423456789012345'),
(10, '1992-06-30', '(11) 94321-2100', '05402-001', 'Rua Oscar Freire, 1200 - Sao Paulo/SP', '523456789012345');

-- Planos do convênio interno CardioLab Care
INSERT INTO planos_carteirinha
    (codigo, nome, valor_mensal, desconto_consulta_percentual, desconto_exame_percentual,
     encaixes_urgentes_mes, teleconsultas_mes, descricao, beneficios_json, ativo)
VALUES
('CARE-ESSENCIAL', 'CardioLab Care Essencial', 39.90, 10, 8, 0, 0,
 'Plano de entrada para acompanhamento preventivo e descontos básicos.',
 '["Carteirinha digital CardioLab","10% em consultas particulares","8% em exames cardiológicos","Histórico unificado no portal"]', 1),
('CARE-PLUS', 'CardioLab Care Plus', 69.90, 20, 15, 1, 1,
 'Convênio interno para pacientes em acompanhamento recorrente.',
 '["20% em consultas particulares","15% em exames cardiológicos","1 encaixe prioritário por mês","1 teleconsulta de retorno por mês"]', 1),
('CARE-PREMIUM', 'CardioLab Care Premium', 129.90, 35, 25, 2, 2,
 'Cobertura premium para controle cardiológico contínuo.',
 '["35% em consultas particulares","25% em exames cardiológicos","2 encaixes prioritários por mês","2 teleconsultas de retorno por mês"]', 1);

INSERT INTO carteirinhas_pacientes
    (paciente_id, plano_id, numero_carteirinha, titular, situacao, inicio_em, expira_em)
VALUES
(1, 2, 'CLB-2606-00001-DEMO', 'Maria Silva Santos', 'ativa', CURDATE(), CURDATE() + INTERVAL 1 YEAR),
(3, 1, 'CLB-2606-00003-DEMO', 'Luciana Araujo Martins', 'em_analise', CURDATE(), CURDATE() + INTERVAL 1 YEAR);

-- Dados do médico
INSERT INTO medicos (usuario_id, especialidade, crm, rqe, biografia, expediente_inicio, expediente_fim) VALUES
(2, 'Cardiologia', 'CRM/SP 123456', 'RQE 78901', 
 'Cardiologista com 15 anos de experiência. Especialista em ecocardiografia e insuficiência cardíaca. Membro da Sociedade Brasileira de Cardiologia.',
 '08:00:00', '18:00:00');

INSERT INTO medicos (usuario_id, especialidade, crm, rqe, biografia, expediente_inicio, expediente_fim) VALUES
(4, 'Arritmologia e Holter', 'CRM/SP 221904', 'RQE 55412',
 'Especialista em arritmias, Holter 24h e investigacao de palpitacoes, com abordagem direta e preventiva.',
 '07:30:00', '16:30:00'),
(5, 'Ecocardiografia', 'CRM/SP 198772', 'RQE 48021',
 'Foco em ecocardiograma, valvopatias e acompanhamento de insuficiencia cardiaca em adultos.',
 '09:00:00', '19:00:00'),
(6, 'Cardiologia Preventiva', 'CRM/SP 205889', 'RQE 61204',
 'Atua em check-up cardiologico, hipertensao, risco cardiovascular e plano de mudanca de habitos.',
 '08:00:00', '17:00:00');

-- Serviços cardiológicos
INSERT INTO servicos (nome, descricao, preparo, duracao_minutos, indicacao) VALUES
('Consulta Cardiológica', 
 'Avaliação completa da saúde cardiovascular com anamnese detalhada, exame físico e orientações personalizadas.',
 'Levar exames anteriores, lista de medicamentos em uso e cartão do convênio.',
 30, 'Check-up cardiovascular, sintomas como dor no peito, falta de ar, palpitações.'),

('Eletrocardiograma (ECG)', 
 'Registro da atividade elétrica do coração através de eletrodos posicionados no corpo.',
 'Não é necessário jejum. Evitar cremes ou loções no tórax. Usar roupas confortáveis.',
 15, 'Dor no peito, arritmias, palpitações, check-up, pré-operatório.'),

('Ecocardiograma', 
 'Ultrassom do coração que avalia estrutura, função e fluxo sanguíneo em tempo real.',
 'Não é necessário preparo especial. Usar roupa de duas peças para facilitar o exame.',
 40, 'Sopros cardíacos, insuficiência cardíaca, doenças valvulares, hipertensão.'),

('Holter 24h', 
 'Monitoramento contínuo do ritmo cardíaco por 24 horas através de um aparelho portátil.',
 'Tomar banho antes da instalação. Não usar cremes no tórax. Usar roupa confortável com botões na frente. NÃO molhar o aparelho.',
 1440, 'Palpitações, tonturas, desmaios, avaliação de arritmias.'),

('MAPA (Monitorização Ambulatorial da Pressão Arterial)', 
 'Medição automática da pressão arterial a cada 15-20 minutos durante 24 horas.',
 'Usar manga curta ou blusa folgada no braço. Manter atividades normais. Anotar horários de sono e atividades.',
 1440, 'Hipertensão arterial, avaliação de tratamento, hipertensão mascarada.'),

('Teste Ergométrico', 
 'Avaliação do coração durante esforço físico progressivo em esteira ergométrica.',
 'Jejum de 2 horas. Usar roupa esportiva e tênis. Manter medicamentos conforme orientação médica. Evitar fumar 2 horas antes.',
 45, 'Dor torácica, avaliação de capacidade funcional, pré-operatório, aptidão física.'),

('Doppler Vascular', 
 'Ultrassom dos vasos sanguíneos para avaliar o fluxo de sangue em artérias e veias.',
 'Não é necessário preparo especial para membros. Para abdome, jejum de 6 horas.',
 30, 'Varizes, trombose, aneurismas, doença arterial periférica.'),

('Check-up Cardiológico', 
 'Pacote completo de avaliação cardiovascular com consulta, ECG e exames laboratoriais.',
 'Jejum de 12 horas para exames de sangue. Levar exames anteriores.',
 60, 'Prevenção cardiovascular, pacientes com fatores de risco, acima de 40 anos.'),

('Avaliação Pré-operatória', 
 'Avaliação do risco cardíaco antes de procedimentos cirúrgicos.',
 'Levar solicitação do cirurgião, exames anteriores e lista de medicamentos.',
 30, 'Pacientes com cirurgia agendada que necessitam de liberação cardiológica.'),

('Teleconsulta', 
 'Consulta cardiológica por vídeo com a mesma qualidade do atendimento presencial.',
 'Ter acesso a computador ou celular com câmera e internet estável. Separar exames anteriores.',
 30, 'Retornos, orientações, acompanhamento de pacientes crônicos, segunda opinião.');

-- Consultas de exemplo
INSERT INTO consultas (paciente_id, medico_id, servico_id, data_consulta, horario_consulta, duracao_minutos, situacao) VALUES
(1, 1, 1, CURDATE() + INTERVAL 3 DAY, '09:00:00', 30, 'agendada'),
(1, 1, 2, CURDATE() + INTERVAL 5 DAY, '10:00:00', 15, 'agendada'),
(1, 1, 3, CURDATE() - INTERVAL 30 DAY, '14:00:00', 40, 'finalizada'),
(1, 1, 1, CURDATE() - INTERVAL 60 DAY, '11:00:00', 30, 'finalizada');

INSERT INTO consultas (paciente_id, medico_id, servico_id, data_consulta, horario_consulta, duracao_minutos, situacao) VALUES
(2, 2, 4, CURDATE() + INTERVAL 1 DAY, '08:00:00', 30, 'confirmada'),
(3, 3, 3, CURDATE() + INTERVAL 1 DAY, '09:00:00', 40, 'agendada'),
(4, 4, 8, CURDATE() + INTERVAL 2 DAY, '10:30:00', 60, 'agendada'),
(5, 2, 2, CURDATE() + INTERVAL 2 DAY, '11:00:00', 15, 'confirmada'),
(2, 1, 1, CURDATE() - INTERVAL 12 DAY, '15:00:00', 30, 'finalizada'),
(3, 4, 6, CURDATE() - INTERVAL 20 DAY, '08:30:00', 45, 'finalizada');

-- Dia demonstrativo sem vagas para exibir o calendario em vermelho.
INSERT INTO consultas (paciente_id, medico_id, servico_id, data_consulta, horario_consulta, duracao_minutos, situacao) VALUES
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '08:00:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '08:30:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '09:00:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '09:30:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '10:00:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '10:30:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '11:00:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '11:30:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '12:00:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '12:30:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '13:00:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '13:30:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '14:00:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '14:30:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '15:00:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '15:30:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '16:00:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '16:30:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '17:00:00', 30, 'confirmada'),
(1, 1, 1, CURDATE() + INTERVAL 10 DAY, '17:30:00', 30, 'confirmada');

-- Exames de exemplo
INSERT INTO resultados_exames (paciente_id, medico_id, servico_id, titulo, arquivo_url, tipo_resultado) VALUES
(1, 1, 2, 'Eletrocardiograma - Resultado Normal', '/static/arquivos_enviados/ecg_maria_2024.pdf', 'pdf'),
(1, 1, 3, 'Ecocardiograma - FE 65%', '/static/arquivos_enviados/eco_maria_2024.pdf', 'pdf');

-- Métricas de saúde
INSERT INTO metricas_saude (paciente_id, pressao_arterial, frequencia_cardiaca, peso, imc, glicemia, colesterol, medido_em) VALUES
(1, '130/85', 72, 68.5, 26.3, 95.0, 195.0, NOW() - INTERVAL 90 DAY),
(1, '128/82', 70, 67.8, 26.0, 92.0, 190.0, NOW() - INTERVAL 60 DAY),
(1, '125/80', 68, 67.0, 25.7, 88.0, 185.0, NOW() - INTERVAL 30 DAY),
(1, '122/78', 66, 66.5, 25.5, 85.0, 180.0, NOW());

INSERT INTO metricas_saude (paciente_id, pressao_arterial, frequencia_cardiaca, peso, imc, glicemia, colesterol, medido_em) VALUES
(2, '118/76', 64, 81.2, 24.9, 90.0, 172.0, NOW() - INTERVAL 15 DAY),
(3, '142/88', 78, 72.4, 27.2, 108.0, 218.0, NOW() - INTERVAL 10 DAY),
(4, '135/84', 74, 88.0, 28.0, 97.0, 205.0, NOW() - INTERVAL 8 DAY),
(5, '110/70', 62, 59.5, 22.8, 86.0, 168.0, NOW() - INTERVAL 6 DAY);

-- Prontuário
INSERT INTO prontuarios (paciente_id, medico_id, observacoes, medicamentos, alerta_risco) VALUES
(1, 1, 'Paciente em acompanhamento por hipertensão arterial leve. Boa adesão ao tratamento. Exames recentes dentro da normalidade. Orientada sobre dieta hipossódica e atividade física regular.',
 'Losartana 50mg 1x/dia, AAS 100mg 1x/dia',
 'moderado');

-- Notificações
INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo, lida) VALUES
(3, 'Consulta Próxima', 'Sua consulta com Dr. Ricardo Mendes está agendada para daqui a 3 dias às 09:00.', 'lembrete', 0),
(3, 'Exame Disponível', 'O resultado do seu Eletrocardiograma já está disponível para visualização.', 'sucesso', 0),
(3, 'Confirme sua Presença', 'Por favor, confirme sua presença na consulta agendada.', 'atencao', 0);

-- Artigos educativos
INSERT INTO artigos (titulo, categoria, conteudo, imagem_url) VALUES
('10 Dicas para Manter seu Coração Saudável', 'Saúde do Coração',
 'Manter o coração saudável é fundamental para uma vida longa e com qualidade. A saúde cardiovascular depende de hábitos diários que muitas vezes são simples de adotar. Aqui estão 10 dicas essenciais:\n\n1. **Pratique exercícios regularmente** - Pelo menos 150 minutos por semana de atividade moderada.\n2. **Mantenha uma alimentação equilibrada** - Priorize frutas, verduras, grãos integrais e proteínas magras.\n3. **Controle o peso** - O sobrepeso aumenta o risco de doenças cardíacas.\n4. **Não fume** - O tabagismo é um dos principais fatores de risco cardiovascular.\n5. **Controle o estresse** - Pratique meditação, yoga ou atividades relaxantes.\n6. **Durma bem** - 7 a 8 horas de sono por noite são ideais.\n7. **Monitore a pressão arterial** - Hipertensão é silenciosa e perigosa.\n8. **Controle o colesterol** - Faça exames regulares.\n9. **Limite o consumo de álcool** - Moderação é a chave.\n10. **Faça check-ups regulares** - Prevenção é o melhor tratamento.',
 ''),

('Pressão Alta: O Inimigo Silencioso', 'Pressão Alta',
 'A hipertensão arterial é conhecida como o "inimigo silencioso" porque raramente apresenta sintomas nos estágios iniciais. No Brasil, cerca de 32% da população adulta é hipertensa.\n\n**O que é pressão alta?**\nA pressão arterial é a força que o sangue exerce nas paredes das artérias. Quando essa pressão é constantemente elevada (acima de 140/90 mmHg), temos a hipertensão.\n\n**Fatores de risco:**\n- Histórico familiar\n- Sedentarismo\n- Excesso de sal\n- Obesidade\n- Estresse\n- Tabagismo\n- Consumo excessivo de álcool\n\n**Como prevenir:**\n- Reduza o consumo de sal\n- Pratique exercícios\n- Mantenha peso saudável\n- Monitore regularmente\n- Siga o tratamento médico',
 ''),

('Colesterol: Entenda os Números', 'Colesterol',
 'O colesterol é uma substância gordurosa essencial para o organismo, mas em excesso pode ser prejudicial ao coração.\n\n**Tipos de colesterol:**\n- **LDL (ruim):** Quando elevado, acumula-se nas artérias formando placas.\n- **HDL (bom):** Ajuda a remover o colesterol das artérias.\n- **Triglicerídeos:** Outro tipo de gordura no sangue.\n\n**Valores de referência:**\n- Colesterol total: até 200 mg/dL\n- LDL: até 130 mg/dL\n- HDL: acima de 40 mg/dL (homens) e 50 mg/dL (mulheres)\n- Triglicerídeos: até 150 mg/dL\n\n**Como controlar:**\n- Alimentação rica em fibras\n- Exercícios aeróbicos\n- Reduzir gorduras saturadas\n- Medicamentos quando necessário\n- Acompanhamento médico regular',
 ''),

('Diabetes e Coração: Uma Relação Perigosa', 'Diabetes e Coração',
 'Pessoas com diabetes têm risco 2 a 4 vezes maior de desenvolver doenças cardiovasculares. O excesso de açúcar no sangue danifica os vasos sanguíneos e os nervos que controlam o coração.\n\n**Por que o diabetes afeta o coração?**\nNíveis elevados de glicose causam inflamação nas paredes dos vasos, favorecendo o acúmulo de gordura e a formação de placas de aterosclerose.\n\n**Como proteger seu coração se tem diabetes:**\n- Controle rigoroso da glicemia\n- Monitore a pressão arterial\n- Controle o colesterol\n- Mantenha peso saudável\n- Pratique exercícios regularmente\n- Tome os medicamentos corretamente\n- Faça acompanhamento cardiológico anual',
 ''),

('Prevenção Cardiovascular para Idosos', 'Prevenção para Idosos',
 'Após os 60 anos, os cuidados com o coração precisam ser redobrados. O envelhecimento natural traz alterações cardiovasculares que exigem atenção especial.\n\n**Alterações comuns no coração do idoso:**\n- As artérias ficam mais rígidas\n- O coração pode aumentar ligeiramente\n- A frequência cardíaca máxima diminui\n- A pressão arterial tende a subir\n\n**Dicas de prevenção:**\n- Caminhadas diárias de 30 minutos\n- Alimentação rica em peixes, frutas e vegetais\n- Hidratação adequada\n- Controle de medicamentos\n- Check-up cardiológico anual\n- Vacinação em dia (gripe e pneumonia)\n- Atividades sociais e mentais\n- Sono regular e de qualidade',
 ''),

('Guia Completo de Exames Cardiológicos', 'Exames Cardiológicos',
 'Conheça os principais exames cardiológicos e quando cada um é indicado.\n\n**Eletrocardiograma (ECG):**\nRegistra a atividade elétrica do coração. Rápido, indolor e fundamental para detectar arritmias e isquemia.\n\n**Ecocardiograma:**\nUltrassom do coração que mostra sua estrutura e funcionamento em tempo real. Avalia válvulas, câmaras e função cardíaca.\n\n**Holter 24h:**\nMonitoramento contínuo do ritmo cardíaco. Ideal para detectar arritmias intermitentes.\n\n**MAPA:**\nMonitorização da pressão arterial por 24 horas. Importante para diagnóstico preciso de hipertensão.\n\n**Teste Ergométrico:**\nAvalia o coração durante exercício. Detecta isquemia e avalia capacidade funcional.\n\n**Doppler Vascular:**\nAvalia o fluxo sanguíneo em artérias e veias. Importante para detectar obstruções e tromboses.',
 '');

-- Depoimentos (tipo = 'depoimento', escala 0-10)
INSERT INTO avaliacoes (nome_paciente, tipo, nota, comentario) VALUES
('João Carlos M.', 'depoimento', 10, 'Excelente atendimento! Dr. Ricardo é muito atencioso e explica tudo com clareza. A clínica é moderna e confortável. Recomendo muito.'),
('Ana Paula S.', 'depoimento', 10, 'Fiz meu check-up cardiológico completo e fiquei impressionada com a qualidade dos equipamentos e do atendimento. Equipe muito profissional.'),
('Roberto F.', 'depoimento', 8, 'Ótimo médico e estrutura. Facilidade de agendar online e receber resultados pelo portal. Nota 10 para a praticidade.'),
('Dona Tereza L.', 'depoimento', 10, 'Tenho 78 anos e me sinto muito bem acolhida na CardioLab. Os funcionários são pacientes e carinhosos. O Dr. Ricardo acompanha meu coração há 5 anos.'),
('Paulo H.', 'depoimento', 10, 'O agendamento online mostrou os horários livres e consegui escolher a Dra. Helena pelo perfil. Muito prático.'),
('Luciana M.', 'depoimento', 10, 'Gostei de ver meus exames e orientações em um painel simples. A equipe passa muita segurança.'),
('Marcos R.', 'depoimento', 8, 'Fiz o teste ergometrico com preparo bem explicado e atendimento pontual.');

-- NPS (tipo = 'nps', escala 0-10)
INSERT INTO avaliacoes (paciente_id, tipo, nota, comentario) VALUES
(1, 'nps', 9, 'Muito satisfeita com o atendimento e os resultados dos exames.');

-- Risco cardiovascular inicial (Framingham)
INSERT INTO calculos_risco
(paciente_id, sexo, idade, colesterol_total, hdl, pressao_sistolica, trata_pressao, fumante, diabetes, risco_percentual, classe_risco, recomendacoes_json)
VALUES
(1, 'F', 66, 180, 52, 122, 1, 0, 0, 12.40, 'intermediario',
 JSON_ARRAY('Manter acompanhamento cardiologico regular.', 'Monitorar pressao arterial e perfil lipidico.'));

-- Configuracoes da clinica
INSERT INTO configuracoes_clinica (chave, valor) VALUES
('nome_clinica', 'CardioLab'),
('whatsapp_clinica', '5511999999999'),
('horario_funcionamento', 'Segunda a sexta, 7h às 19h; sábado, 8h às 13h'),
('logo_clinica', '/static/assets/cardiolab-logo-original (1).png')
ON DUPLICATE KEY UPDATE valor = VALUES(valor);

-- Consentimento
UPDATE usuarios SET consentimento_aceito = 1 WHERE email = 'maria@email.com';

-- Log de auditoria
INSERT INTO auditoria (usuario_id, acao, endereco_ip) VALUES
(3, 'LOGIN', '127.0.0.1'),
(3, 'VIEW_DASHBOARD', '127.0.0.1'),
(2, 'LOGIN', '127.0.0.1');
