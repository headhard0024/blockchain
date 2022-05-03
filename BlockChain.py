import hashlib
import json
from pstats import SortKey
import sys
import requests
from urllib.parse import urlparse
from flask import Flask, jsonify, request
from uuid import uuid4
from time import time

class Blockchain(object):
    
    def __init__(self):
        self.chain = []
        self.currentTrxs = [] 
        self.nodes = set()
        self.newBlock(proof=100, previousHash=1)
    
    def newBlock(self, proof, previousHash = None):
        block={
            'index':len(self.chain)+1,
            'timeStamp':time(),
            'trxs' :self.currentTrxs,
            'proof' :proof,
            'previousHash' :previousHash or self.hash(self.chain[-1])
        }
        self.currentTrxs = []
        self.chain.append(block)
        return block
    
    def newTrx(self, sender, recipient, amount):
        self.currentTrxs.append({'sender':sender, 'recipient':recipient, 'amount':amount})
        return self.lastBlock['index'] + 1
    
    
    @staticmethod
    def hash(block):
        blockString = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(blockString).hexdigest()

    
    @property
    def lastBlock(self):
        return self.chain[-1]

    
    @staticmethod
    def validProof(lastProof, proof, trxs):
        thisProof = f'{proof}{lastProof}{trxs}'.encode()
        thisProofHash = hashlib.sha256(thisProof).hexdigest()
        return thisProofHash[:4] == '0000'

    
    def ProofOfWork(self, lastProof, trxs):
        proof = 0
        while self.validProof(lastProof , proof, trxs) is False:
            proof +=1
        print(trxs)
        return proof


    def registerNode(self, address):
        pasedUrl = urlparse(address)
        
        if pasedUrl:
            self.nodes.add(pasedUrl.netloc)

        
    def validChain(self, chain):
        lastBlock = chain[0]
        currentIndex = 1
        while currentIndex < len(chain):
            block = chain[currentIndex]
            
            if(block['previousHash'] != self.hash(lastBlock)):
                return False

            if not self.validProof(lastBlock['proof'], block['proof'], block['trxs']):
                return False
            
            lastBlock = block
            currentIndex += 1
        
        return True
    
    
    def resolveConflicts(self):
        neighbours = self.nodes
        newChain = None
        
        maxLength = len(self.chain)
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if(response.status_code == 200):
                lenght = response.json()['length']
                chain = response.json()['chain']
                 
                if(lenght > maxLength and self.validChain(chain)):
                    maxLength = lenght
                    newChain = chain
            
            if newChain:
                self.chain = newChain
                return True
        
        return False
                
        

app = Flask(__name__)
nodeId = str(uuid4())

blockchain = Blockchain()

@app.route('/mine')
def mine():
    lastBlock = blockchain.lastBlock
    lastProof = blockchain.lastBlock['proof']
    
    blockchain.newTrx(sender="0" ,recipient=nodeId, amount=50)
    
    proof = blockchain.ProofOfWork(lastProof, blockchain.currentTrxs)
    
    previousHash = blockchain.hash(lastBlock)
    block = blockchain.newBlock(proof, previousHash)
    
    res = {
        'message': 'new block is create',
        'index': block['index'],
        'trxs': block['trxs'],
        'proof': block['proof'],
        'previousHash': block['previousHash']
    }
    return jsonify(res), 201


@app.route('/trxs/new', methods=['POST'])
def newTrx():
    values = request.get_json()
    thisBlock = blockchain.newTrx(values['sender'], values['recipient'], values['amount'])
    res = {'message': f'your trx is add to block {thisBlock}'}
    return jsonify(res), 201


@app.route('/chain')
def fullChain():
    res={
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(res), 200


@app.route('/nodes/register', methods=['POST'])
def registerNode():
    values = request.get_json()
    nodes = values.get('nodes')
    
    for node in nodes:
        blockchain.registerNode(node)
    
    res = {'message': 'node added',
            'totalNodes': list(blockchain.nodes)}
    
    return jsonify(res), 201


# @app.route('/nodes/list')
# def getNodes():
#     res = {'list': blockchain.nodes}
#     return jsonify(res), 200


@app.route('/resolve')
def consensus():
    replaced = blockchain.resolveConflicts()
    if replaced:
        res = {'message': 'chain is replaced',
               'chain': blockchain.chain}
    else:
        res = {'message': 'im the best',
               'chain': blockchain.chain}
    
    return jsonify(res), 200    


if __name__ == '__main__':
    app.run(host='0.0.0.0', port = sys.argv[1])
    # app.run(host='127.0.0.1', port = '8001')
    