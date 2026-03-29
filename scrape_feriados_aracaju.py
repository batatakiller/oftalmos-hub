import sys
import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

url = "https://feriados.com.br/SE/Aracaju"

async def run(target_year=None):
    if not target_year:
        target_year = datetime.now().year
        
    print(f"🚀 [Scraper 3.1] Acedendo a {url} para o ano {target_year}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            
            for _ in range(5):
                await page.mouse.wheel(0, 1500)
                await asyncio.sleep(1)

            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            feriados = []
            # Blocos dos meses
            month_sections = soup.find_all("div", class_="rounded-lg")
            
            for section in month_sections:
                header = section.find("h3")
                if not header: continue
                month_text = header.get_text(strip=True)
                if str(target_year) not in month_text: continue
                month_name = month_text.split(" ")[0]
                
                # Cada item de feriado está numa div clicável ou link
                # Vamos buscar os números grandes dentro dos círculos (calendário visual)
                items = section.find_all("div", recursive=False)
                # No novo layout, os feriados estão dentro de botões ou divs interativas
                # Vou buscar por qualquer div que contenha o texto de um tipo de feriado
                potential_items = section.find_all("div", class_=lambda x: x and "flex" in x)
                
                for p_item in potential_items:
                    text = p_item.get_text(" ", strip=True)
                    # Procurar padrão: "01 Janeiro Confraternização..."
                    import re
                    # Regex para: [DIA] [NOME DO Feriado (pelo link)] [TIPO]
                    link = p_item.find("a", class_=lambda x: x and "text-foreground" in x)
                    if not link: continue
                    
                    name = link.get_text(strip=True)
                    
                    # O dia está geralmente num span com classe p-2, font-bold etc.
                    # Vamos buscar o primeiro número que aparece no CONTAINER PARENTE
                    day_match = re.search(r'(\d{1,2})', text)
                    if day_match:
                        day = day_match.group(1)
                        
                        tipo = "Feriado"
                        if "Nacional" in text: tipo = "Feriado Nacional"
                        elif "Estadual" in text: tipo = "Feriado Estadual"
                        elif "Municipal" in text: tipo = "Feriado Municipal"
                        elif "Facultativo" in text: tipo = "Ponto Facultativo"
                        
                        # Limpeza final: se o nome contiver "Dom", "Seg" etc, não é o nome real
                        name = name.split("(")[0].strip()
                        
                        feriados.append({
                            "data": f"{int(day):02d} {month_name}",
                            "nome": name,
                            "tipo": tipo
                        })

            unique_feriados = []
            seen = set()
            for f in feriados:
                id_tuple = (f['data'], f['nome'])
                if id_tuple not in seen:
                    unique_feriados.append(f)
                    seen.add(id_tuple)

            output = f"feriados_aracaju_{target_year}.json"
            with open(output, "w", encoding="utf-8") as f:
                json.dump(unique_feriados, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Sucesso! {len(unique_feriados)} feriados mapeados em {output}")

        except Exception as e:
            print(f"❌ Erro operacional: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    t_year = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        t_year = int(sys.argv[1])
    asyncio.run(run(t_year))
