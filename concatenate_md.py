import os
import re

def clean_content(content):
    # 1. Remover Imagens Base64 ou decorativas
    # Pattern: ![texto](data:image/...) ou ![texto](https://... .png/jpg) que são ícones
    content = re.sub(r'!\[.*?\]\(data:image\/.*?;base64,.*?\)', '', content)
    content = re.sub(r'!\[.*?\]\(.*?\/assets\/img\/.*?\)', '', content) # Remove ícones de assets
    
    # 2. Limpar Breadcrumbs (Ex: * Início / Cirurgias)
    content = re.sub(r'\*\s*Início\s*\/.*', '', content)
    
    # 3. Tratar Links de Agendamento (Manter o informativo, remover o ruído de botão)
    # Procurar por links de WhatsApp e simplificar
    content = re.sub(r'\[(Agende Sua Consulta|Marque uma Consulta|Agendar um Exame|Agendar uma Cirurgia|Tire suas Dúvidas|Fale direto pelo Whatsapp).*?\]\((https:\/\/wa\.me\/|https:\/\/api\.whatsapp\.com\/|mailto:).*?\)', 
                     r'**Agendamento:** \g<2>5579998781777', content)
    
    # 4. Remover botões de "Mais Informações" que apontam para páginas que já estão aqui
    content = re.sub(r'\[Mais Informações.*?\]\(.*?\)', '', content)
    content = re.sub(r'\[Entre em Contato.*?\]\(.*?\)', '', content)
    
    # 5. Converter links de âncora [Texto](#) em apenas Texto
    content = re.sub(r'\[(.*?)\]\(#\)', r'\1', content)
    
    # 6. Limpeza de espaços extras e linhas vazias excessivas
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()

def clean_filename(filename):
    name = filename.replace('.md', '')
    if '_' in name:
        name = name.split('_')[-1]
    return name.replace('-', ' ').title()

def main():
    source_dir = '/Users/daniel/N8N Oftalmos/knowledge_base/markdown'
    output_file = '/Users/daniel/N8N Oftalmos/knowledge_base/consolidado.md'
    
    # Arquivos a serem ignorados (Redundantes)
    ignored_files = ['home.md', 'index.md', 'nossos-exames.md'] # 'nossos-exames' também costuma ser sumarizado
    
    files = sorted([f for f in os.listdir(source_dir) if f.endswith('.md') and f not in ignored_files])
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write('# Base de Conhecimento Oftalmos - Consolidado e Otimizado\n')
        outfile.write('> Este documento contém informações detalhadas extraídas do site oficial, limpas de elementos de navegação.\n\n')
        
        for filename in files:
            clean_name = clean_filename(filename)
            file_path = os.path.join(source_dir, filename)
            
            with open(file_path, 'r', encoding='utf-8') as infile:
                raw_content = infile.read()
                cleaned = clean_content(raw_content)
                
                if cleaned:
                    outfile.write(f'---\n\n## {clean_name}\n\n')
                    outfile.write(cleaned)
                    outfile.write('\n\n')
                    
    print(f"Sucesso! {len(files)} arquivos processados e otimizados em {output_file}")

if __name__ == "__main__":
    main()
