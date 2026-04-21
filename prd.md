PRD: Dashboard Clínico Fullstack - Oftalmos
Stack: Next.js 14 (App Router), Tailwind CSS, Shadcn/UI, Lucide React (Ícones), Supabase (Backend/Realtime), Evolution API.

1. Visão Geral
Sistema web de alta performance para gestão de pacientes e consultas. O objetivo é oferecer uma interface reativa onde o médico e a recepção possam monitorar atendimentos em tempo real, com chat integrado e visualização de exames.

2. Requisitos Técnicos (Vibecode/Next.js)
Framework: Next.js com TypeScript.

UI Library: Shadcn/UI (utilizando componentes como Table, Card, Dialog, Badge, Tabs e ScrollArea).

State Management: React Hooks (ou TanStack Query para cache de dados).

Banco de Dados: Conexão direta via @supabase/supabase-js.

3. Módulos e Componentes Shadcn/UI
Módulo A: Kanban de Atendimento (CRM)
Componente: Card e Drag and Drop (pode usar dnd-kit ou apenas colunas reativas).

Colunas: "Aguardando", "Agendado", "Triagem", "Em Atendimento", "Finalizado".

Lógica: Cada card representa uma linha da tabela consultas. Ao mover o card, o status no Supabase deve ser atualizado via RPC ou Update direto.

Módulo B: Chat de Pacientes (Evolution API Integration)
Layout: Sidebar esquerda (ScrollArea) com lista de contatos e área central de chat.

Mensagens: Componentes de balão de chat diferenciando inbound e outbound.

Renderização de Mídia: * Se tipo === 'image', usar componente AspectRatio do Shadcn para exibir a URL do Bucket do Supabase.

Se tipo === 'video', renderizar o player com controles.

Módulo C: Gestão de Agenda
Componente: Calendar do Shadcn/UI integrado com a tabela horarios_disponiveis.

Visualização: Lista de horários livres vs. ocupados (confrontando horarios_disponiveis com consultas).

4. Integração Supabase (Realtime)
Requisito Crítico: O Dashboard deve usar supabase.channel() para ouvir mudanças na tabela whatsapp_mensagens e consultas.

Efeito: Se a Íris (n8n) agendar uma consulta, o card deve aparecer no Kanban do médico instantaneamente sem recarregar a página.

5. Endpoints da Evolution API
O Next.js deve ter uma API Route (/api/whatsapp/send) para disparar mensagens manuais.

O componente de input de texto no chat deve chamar essa rota para enviar mensagens via Evolution API.