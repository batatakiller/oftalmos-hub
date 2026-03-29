require('dotenv').config();
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
  res.status(200).send('OK'); // Responder rápido para não gerar timeout

  try {
    const body = req.body;
    const event = body?.event;

    console.log(`[WEBHOOK] Evento recebido: ${event}`);

    if (event !== 'messages.upsert') return;

    const data = body.data;
    const key = data?.key;
    const msg = data?.message;

    if (!key || !msg || key.fromMe) return; // Ignorar mensagens próprias

    const remoteJid = key.remoteJid || '';
    const phone = remoteJid.split('@')[0].replace(/\D/g, '');
    const text = msg.conversation
      || msg.extendedTextMessage?.text
      || msg.imageMessage?.caption
      || '';

    if (!text || !phone) return;

    console.log(`[WEBHOOK INBOUND] ${phone}: ${text.substring(0, 40)}`);

    const { error } = await supabase.from('whatsapp_chat').insert([{
      phone,
      message: text,
      direction: 'inbound',
      status: 'received',
      sender_phone: phone
    }]);

    if (error) console.error('[WEBHOOK] Erro ao salvar:', error.message);
    else console.log(`[WEBHOOK] ✅ Mensagem de ${phone} salva no Supabase!`);

  } catch (err) {
    console.error('[WEBHOOK] Erro geral:', err.message);
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
