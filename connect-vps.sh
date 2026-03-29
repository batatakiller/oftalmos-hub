#!/bin/bash

# Script para conexão rápida ao VPS Oracle
# IP: 147.15.99.72
# Usuário: ubuntu

KEY_PATH="./ssh-key-2026-03-02.key"
USER="ubuntu"
IP="147.15.99.72"

if [ ! -f "$KEY_PATH" ]; then
    echo "Erro: Chave não encontrada em $KEY_PATH"
    exit 1
fi

chmod 600 "$KEY_PATH"
ssh -i "$KEY_PATH" "$USER@$IP"
