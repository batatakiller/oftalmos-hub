import sys
import json
import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

url = "https://feriados.com.br/SE/Aracaju"

async def run(target_year=None):
    if not target_year:
        target_year = datetime.now().year
        
    print(f"🚀 [Scraper] Acedendo a {url} para o ano {target_year}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5) # Aguarda renderização JS
            
            # Scroll para carregar meses distantes se necessário
            for _ in range(5):
                await page.mouse.wheel(0, 1500)
                await asyncio.sleep(1)

            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            resultados_formatados = []
            
            # Encontrar blocos de meses
            month_sections = soup.find_all("div", class_="rounded-lg")
            
            for section in month_sections:
                header = section.find("h3")
                if not header: continue
                
                month_text = header.get_text(strip=True).lower()
                # Verifica se o ano está correto no header do mês
                if str(target_year) not in month_text: continue
                
                month_name = month_text.split(" ")[0].capitalize()
                
                # Encontrar itens dentro do mês
                potential_items = section.find_all("div", class_=lambda x: x and "flex" in x)
                
                for p_item in potential_items:
                    text = p_item.get_text(" ", strip=True)
                    link = p_item.find("a", class_=lambda x: x and "text-foreground" in x)
                    if not link: continue
                    
                    name = link.get_text(strip=True)
                    
                    # Extrair o dia (primeiro número no bloco)
                    day_match = re.search(r'(\d{1,2})', text)
                    if day_match:
                        day = day_match.group(1)
                        
                        # Simplificar o Tipo
                        tipo = ""
                        if "Nacional" in text: tipo = "Nacional"
                        elif "Estadual" in text: tipo = "Estadual"
                        elif "Municipal" in text: tipo = "Municipal"
                        elif "Facultativo" in text: tipo = "Facultativo"
                        else: tipo = "Data Comemorativa"
                        
                        # Limpeza do nome (remove parênteses extras como dias da semana)
                        clean_name = re.sub(r'\(.*?\)', '', name).strip()
                        
                        # Montar a string conforme o exemplo: [Mês] [Ano] [Dia] [Nome] [Tipo]
                        linha = f"{month_name} {target_year} {int(day)} {clean_name} {tipo}"
                        resultados_formatados.append(linha)

            # Remover duplicatas mantendo ordem
            final_list_strings = list(dict.fromkeys(resultados_formatados))
            
            # Criar lista estruturada para o JSON (melhor para Supabase)
            final_list_objects = []
            seen = set()
            
            # Processar novamente para pegar os campos separados
            for section in month_sections:
                header = section.find("h3")
                if not header: continue
                month_text = header.get_text(strip=True).lower()
                if str(target_year) not in month_text: continue
                month_name = month_text.split(" ")[0].capitalize()
                
                potential_items = section.find_all("div", class_=lambda x: x and "flex" in x)
                for p_item in potential_items:
                    text = p_item.get_text(" ", strip=True)
                    link = p_item.find("a", class_=lambda x: x and "text-foreground" in x)
                    if not link: continue
                    name = link.get_text(strip=True)
                    day_match = re.search(r'(\d{1,2})', text)
                    if day_match:
                        day = int(day_match.group(1))
                        # Mapeamento para tipos limpos e minúsculos
                        raw_tipo = text.lower()
                        if "nacional" in raw_tipo: tipo = "nacional"
                        elif "estadual" in raw_tipo: tipo = "estadual"
                        elif "municipal" in raw_tipo: tipo = "municipal"
                        elif "facultativo" in raw_tipo: tipo = "facultativo"
                        else: tipo = "data_comemorativa"
                        
                        clean_name = re.sub(r'\(.*?\)', '', name).strip()
                        
                        id_tuple = (target_year, month_name, day, clean_name)
                        if id_tuple not in seen:
                            final_list_objects.append({
                                "dia": day,
                                "mes": month_name,
                                "ano": target_year,
                                "nome": clean_name,
                                "tipo": tipo
                            })
                            seen.add(id_tuple)

            # Salvar arquivos
            output_txt = f"feriados_aracaju_{target_year}.txt"
            output_json = f"feriados_aracaju_{target_year}.json"
            
            with open(output_txt, "w", encoding="utf-8") as f:
                f.write("\n".join(final_list_strings))
            
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(final_list_objects, f, indent=2, ensure_ascii=False)
            
            print("\n" + "="*50)
            print(f"✅ Arquivos gerados com sucesso!")
            print(f"📄 TXT (Leitura): {output_txt}")
            print(f"📦 JSON (Supabase): {output_json} com {len(final_list_objects)} itens.")
            print("="*50)

        except Exception as e:
            print(f"❌ Erro operacional: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    t_year = 2026 # Default conforme seu exemplo
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        t_year = int(sys.argv[1])
    asyncio.run(run(t_year))
