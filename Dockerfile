FROM node:20-alpine

WORKDIR /app

# Copiar dependências primeiro (cache layer)
COPY package*.json ./
RUN npm install --omit=dev

# Copiar código da aplicação
COPY server.js ./
COPY public/ ./public/

EXPOSE 3001

CMD ["node", "server.js"]
