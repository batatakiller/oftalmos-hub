require('dotenv').config();
// VERSION: 2026-03-29 14:43 - Force Redeploy
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const { createClient } = require('@supabase/supabase-js');

const app = express();
const PORT = process.env.PORT || 3001;

// MIDDLEWARES - DEVE VIR ANTES DE QUALQUER ROTA
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// SUPABASE CLIENT - DEVE VIR ANTES DAS ROTAS
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// ─────────────────────────────────────────────────────────────
// WEBHOOK - RECEBER MENSAGENS INBOUND DA EVOLUTION API
// A Evolution API envia POST para esta rota quando chega msg
// ─────────────────────────────────────────────────────────────
app.post('/webhook/evolution', async (req, res) => {
  // 1. Responder rápido para evitar timeout
  res.status(200).send('OK');

  try {
    let body = req.body;

    // DEBUG: Logar tudo o que chega para descobrir o formato exato
    console.log(`[WEBHOOK] ${new Date().toISOString()} - Payload bruto recebido:`, 
      typeof body === 'string' ? `String (${body.length} chars)` : 'Objeto JSON');

    // Suporte caso o Evolution API envie em Base64
    if (typeof body === 'string' && body.length > 0) {
      try {
        const decoded = Buffer.from(body, 'base64').toString('utf-8');
        body = JSON.parse(decoded);
        console.log('[WEBHOOK] Sucesso ao decodificar Base64');
      } catch (e) {
        // Se não for base64 ou falhar no parse, ignora
        console.log('[WEBHOOK] Recebeu string mas não é Base64 JSON válido');
      }
    }

    const event = body?.event;
    console.log(`[WEBHOOK] Evento detectado: ${event}`);

    // Lista de eventos que queremos processar (adicione outros conforme necessário)
    if (event !== 'messages.upsert') {
      console.log(`[WEBHOOK] Evento '${event}' ignorado.`);
      return;
    }

    const data = body.data;
    const key = data?.key;
    const msg = data?.message;

    // Log detalhado para debug de campos da mensagem
    if (!key || !msg) {
      console.log('[WEBHOOK] Payload incompleto (key ou message ausentes):', JSON.stringify(data).substring(0, 100));
      return;
    }

    if (key.fromMe) {
      console.log('[WEBHOOK] Ignorando mensagem outbound própria.');
      return;
    }

    const remoteJid = key.remoteJid || '';
    const phone = remoteJid.split('@')[0].replace(/\D/g, '');
    
    // Extrair o texto de diferentes formatos de mensagem (conversação simples ou texto estendido)
    const text = msg.conversation
      || msg.extendedTextMessage?.text
      || msg.imageMessage?.caption
      || '';

    if (!text || !phone) {
      console.log(`[WEBHOOK] Texto ou telefone ausente. Phone: ${phone}, Text length: ${text?.length}`);
      return;
    }

    console.log(`[WEBHOOK INBOUND] ✅ Processando msg de ${phone}: ${text.substring(0, 40)}...`);

    // Inserir no Supabase
    const { error } = await supabase.from('whatsapp_chat').insert([{
      phone,
      message: text,
      direction: 'inbound',
      status: 'received',
      sender_phone: phone
    }]);

    if (error) {
      console.error('[WEBHOOK DB ERR]', error.message);
    } else {
      console.log(`[WEBHOOK] ✅ Mensagem de ${phone} salva no Supabase com sucesso.`);
    }

  } catch (err) {
    console.error('[WEBHOOK FATAL ERR]', err.message, err.stack);
  }
});

// ─────────────────────────────────────────────────────────────
// KANBAN CARDS
// ─────────────────────────────────────────────────────────────
app.get('/api/cards', async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('kanban_cards')
      .select('*')
      .order('posicao', { ascending: true });
    if (error) throw error;
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/cards/:id', async (req, res) => {
  const { id } = req.params;
  const updates = req.body;
  try {
    const { data, error } = await supabase
      .from('kanban_cards')
      .update(updates)
      .eq('id', id)
      .select();
    if (error) throw error;
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────
// CHAT HISTORY
// ─────────────────────────────────────────────────────────────
app.get('/api/chat/:phone', async (req, res) => {
  const cleanPhone = req.params.phone.replace(/\D/g, '');
  try {
    const { data, error } = await supabase
      .from('whatsapp_chat')
      .select('*')
      .eq('phone', cleanPhone)
      .order('created_at', { ascending: true });
    if (error) throw error;
    console.log(`[CHAT] ${cleanPhone} → ${data.length} mensagens`);
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────
// ENVIO DE MENSAGENS (OUTBOUND)
// ─────────────────────────────────────────────────────────────
app.post('/api/send', async (req, res) => {
  const { number, text } = req.body;
  const cleanNumber = number.replace(/\D/g, '');

  try {
    // 1. Enviar via Evolution API
    const response = await axios.post(
      `${process.env.EVO_URL}/message/sendText/${process.env.EVO_INSTANCE}`,
      { number: cleanNumber, text, delay: 1000, linkPreview: false },
      { headers: { 'apikey': process.env.EVO_KEY, 'Content-Type': 'application/json' } }
    );

    // 2. Salvar no Supabase (outbound)
    const { error } = await supabase.from('whatsapp_chat').insert([{
      phone: cleanNumber,
      message: text,
      direction: 'outbound',
      status: 'sent',
      sender_phone: 'Oftalmos HUB'
    }]);
    if (error) console.error('[SEND] Erro ao persistir:', error.message);

    res.json(response.data);
  } catch (err) {
    console.error('[SEND ERR]', err.response?.data || err.message);
    res.status(500).json({ error: 'Falha no envio Evolution' });
  }
});

// ─────────────────────────────────────────────────────────────
// PROXY DE FOTO DE PERFIL WHATSAPP
// ─────────────────────────────────────────────────────────────
app.get('/api/proxy-image/:number', async (req, res) => {
  const cleanNumber = req.params.number.replace(/\D/g, '').trim();
  try {
    const response = await axios.post(
      `${process.env.EVO_URL}/chat/fetchProfilePictureUrl/${process.env.EVO_INSTANCE}`,
      { number: cleanNumber },
      { headers: { 'apikey': process.env.EVO_KEY }, timeout: 5000 }
    );

    const imageUrl = response.data?.profilePictureUrl;
    if (!imageUrl) return res.status(404).send('No image');

    const imgResponse = await axios.get(imageUrl, {
      responseType: 'stream',
      timeout: 8000,
      headers: { 'User-Agent': 'WhatsApp/2.0' }
    });

    res.setHeader('Content-Type', imgResponse.headers['content-type'] || 'image/jpeg');
    res.setHeader('Cache-Control', 'public, max-age=3600');
    imgResponse.data.pipe(res);

  } catch (err) {
    console.log(`[AVATAR] Sem foto para ${cleanNumber}`);
    res.status(404).send('Not found');
  }
});

// ─────────────────────────────────────────────────────────────
// START
// ─────────────────────────────────────────────────────────────
app.listen(PORT, '0.0.0.0', () => {
  console.log(`✅ Oftalmos HUB | Porta: ${PORT} | Webhook: /webhook/evolution`);
});
