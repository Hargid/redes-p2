import os
import asyncio
from tcputils import *


class Servidor:
    def __init__(self, rede, porta):
        self.rede = rede
        self.porta = porta
        self.conexoes = {}
        self.callback = None
        self.rede.registrar_recebedor(self._rdt_rcv)

    def registrar_monitor_de_conexoes_aceitas(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que uma nova conexão for aceita
        """
        self.callback = callback

    def _rdt_rcv(self, src_addr, dst_addr, segment):
        src_port, dst_port, seq_no, ack_no, \
            flags, window_size, checksum, urg_ptr = read_header(segment)

        if dst_port != self.porta:
            # Ignora segmentos que não são destinados à porta do nosso servidor
            return
        if not self.rede.ignore_checksum and calc_checksum(segment, src_addr, dst_addr) != 0:
            print('descartando segmento com checksum incorreto')
            return

        payload = segment[4*(flags>>12):]
        id_conexao = (src_addr, src_port, dst_addr, dst_port)

        if (flags & FLAGS_SYN) == FLAGS_SYN:
            #Numero aleatorio para sequência de segmentos do servidor:
            seqAns = int.from_bytes(os.urandom(4), byteorder='big')
            
            #Proximo segmento esperado
            ack_no = seq_no + 1
            
            # A flag SYN estar setada significa que é um cliente tentando estabelecer uma conexão nova
            # TODO: talvez você precise passar mais coisas para o construtor de conexão
            
            conexao = self.conexoes[id_conexao] = Conexao(self, id_conexao, seqAns, ack_no)
            
            # TODO: você precisa fazer o handshake aceitando a conexão. Escolha se você acha melhor
            # fazer aqui mesmo ou dentro da classe Conexao.
            #Handshake -> enviando ID da conexao para o cliente
            handshake = make_header(dst_port, src_port, seqAns, ack_no, FLAGS_SYN|FLAGS_ACK)
            handshake = fix_checksum(handshake, dst_addr, src_addr)
            
            self.rede.enviar(handshake, src_addr)
            
        
       
            
            
            if self.callback:
                self.callback(conexao)
        elif id_conexao in self.conexoes:
            # Passa para a conexão adequada se ela já estiver estabelecida
            self.conexoes[id_conexao]._rdt_rcv(seq_no, ack_no, flags, payload)
        else:
            print('%s:%d -> %s:%d (pacote associado a conexão desconhecida)' %
                  (src_addr, src_port, dst_addr, dst_port))


class Conexao:
    def __init__(self, servidor, id_conexao, seqAns, ackAns):
        self.servidor = servidor
        self.id_conexao = id_conexao
        self.ackAns = ackAns
        #Numero de Sequencia da Conexao
        self.seqAns = seqAns
        self.segmentosResiduais = []
        self.nAckData = {}
        self.callback = None
        self.isConected = True
        self.timer = None
        #asyncio.get_event_loop().call_later(1, self._exemplo_timer)  # um timer pode ser criado assim; esta linha é só um exemplo e pode ser removida
        #self.timer.cancel()   # é possível cancelar o timer chamando esse método; esta linha é só um exemplo e pode ser removida

    def timePause(self):
        # Esta função é só um exemplo e pode ser removida
        #print('Este é um exemplo de como fazer um timer')
        
        #Utilizarei essa funcao pra reenviar os dados que estavam nos segmentos residuais.
        #INSERINDO TIMER
        if self.timer: #reset timer 
            self.timer.cancel()
            self.time = None
        self.timer = asyncio.get_event_loop().call_later(1, self._skip_turn)

        #pass 
        """
        if not (self.segmentosResiduais == []):
            dados = self.segmentosResiduais.pop(0)
            
            self.servidor.rede.enviar(dados, self.id_conexao[2])
            if self.timer: 
                self.timer.cancel()
                self.timer = None
            if (ack_no < self.seqAns):
                self.segmentosResiduais.insert(0, dados)
            self.timer = asyncio.get_event_loop().call_later(1, self._exemplo_timer)
           """
    def _skip_turn(self):
        pass
    
    def _rdt_rcv(self, seq_no, ack_no, flags, payload):
        # TODO: trate aqui o recebimento de segmentos provenientes da camada de rede.
        # Chame self.callback(self, dados) para passar dados para a camada de aplicação após
        # garantir que eles não sejam duplicados e que tenham sido recebidos em ordem.
        
        #Conexão está ativa
        if self.isConected:
            if ((FLAGS_ACK & flags) == FLAGS_ACK ):
                if (seq_no == self.ackAns):
                    if len(payload) > 0:
                        self.ackAns+= len(payload)
                        self.callback(self, payload)
                        ackMsg = make_header(self.id_conexao[3], self.id_conexao[1], self.seqAns, self.ackAns, FLAGS_ACK)
                        self.servidor.rede.enviar(fix_checksum(ackMsg, self.id_conexao[0], self.id_conexao[2]), self.id_conexao[2])
                elif (ack_no > self.seqAns ):
                    self.seqAns = ack_no +1
                elif (ack_no < self.ackAns): #ack_no > self.seqAns
                    #COMO REENVIAR DADOS?
                    self.ackAns = ack_no + 1
                    #self.enviar(self.segmentosResiduais().pop())
                    if (len(self.segmentosResiduais) > 0):
                        payload = self.segmentosResiduais.pop(0)
                        self.ackAns+= len(payload)
                        self.callback(self, payload)
                        ackMsg = make_header(self.id_conexao[3], self.id_conexao[1], self.seqAns, self.ackAns, FLAGS_ACK)
                        self.timePause
            else:# CASOS POSSIVEIS: seq_no < self.ackAns; seq_no > self.ackAns, seq_no == self.ackAns e ¬FLAG_ACKS
                #FLAGS_ACK False
                self.timer = syncio.get_event_loop().call_later(1, self._timePause) 
                #if (seq_no == self.ackAns) and (ack_no == self.seqAns) and ((FLAGS_ACK & flags) == FLAGS_ACK ):
                
            
            #Pedido de Encerramento de conexões
            if (flags & FLAGS_FIN) == FLAGS_FIN:
                self.callback(self, b'')
                self.ackAns+= 1
                self.fechar()
            
        
        

    # Os métodos abaixo fazem parte da API

    def registrar_recebedor(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que dados forem corretamente recebidos
        """
        self.callback = callback

    def enviar(self, dados):
        """
        Usado pela camada de aplicação para enviar dados
        """
        # TODO: implemente aqui o envio de dados.
        # Chame self.servidor.rede.enviar(segmento, dest_addr) para enviar o segmento
        # que você construir para a camada de rede.
        
        dadosResiduais = b''
        ackMsg = make_header(self.id_conexao[3], self.id_conexao[1], self.seqAns+1, self.ackAns, FLAGS_ACK)
        if len(dados) <= MSS: #Cabe de uma vez
            self.seqAns+= len(dados)
            enviarDados = ackMsg + dados
            
        else: #Necessario dividir
            self.seqAns+=MSS  
            enviarDados = ackMsg + dados[:MSS]
            dadosResiduais = dados[MSS:]
        
	
        enviarDados = fix_checksum(enviarDados, self.id_conexao[0], self.id_conexao[2])
        self.segmentosResiduais.append(enviarDados)
        self.servidor.rede.enviar(enviarDados, self.id_conexao[2])
        
        self.timePause
        
        if len(dadosResiduais) > 0:
            self.enviar(dadosResiduais)
        

    def fechar(self):
        """
        Usado pela camada de aplicação para fechar a conexão
        """
        # TODO: implemente aqui o fechamento de conexão
        finMsg = make_header(self.id_conexao[3], self.id_conexao[1], self.seqAns+1, self.ackAns, FLAGS_ACK | FLAGS_FIN)
        finMsg = fix_checksum(finMsg, self.id_conexao[0], self.id_conexao[2])
        self.servidor.rede.enviar(finMsg, self.id_conexao[2])
        self.isConected = False
        
        
        
