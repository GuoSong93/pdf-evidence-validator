"""Original text PDF fixtures, created with pypdf only."""
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject

CASES=('normal','missing-year','duplicate-year','mixed-scenario','wrong-ratio')
def generate(directory:Path):
 directory.mkdir(parents=True,exist_ok=True)
 for case in CASES:
  writer=PdfWriter();page=writer.add_blank_page(width=595,height=842)
  font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
  page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
  content=['0.07 0.17 0.27 rg 40 702 515 100 re f']
  def text(x,y,size,label,color='0.09 0.18 0.27'):
   escaped=label.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
   content.append(f'{color} rg BT /F1 {size} Tf {x} {y} Td ({escaped}) Tj ET')
  text(58,766,18,'EVIDENCE LAB / SYNTHETIC REPORT','1 1 1')
  text(58,736,10,'Not a financial product. No real customer data.','0.65 0.86 0.84')
  text(50,662,12,'Principal: 1000.00 USD | Scenario: BASE | Years: 1-5')
  text(50,631,12,'Scenario    Year     End value USD     Ratio percent')
  years=[1,2,3,4,5]
  if case=='missing-year':years.remove(3)
  if case=='duplicate-year':years=[1,2,2,4,5]
  for i,year in enumerate(years):
   scenario='UPSIDE' if case=='mixed-scenario' and year==3 else 'BASE'
   ratio=999 if case=='wrong-ratio' and year==3 else 100+10*year
   y=592-i*42;content.append(f'0.94 0.96 0.97 rg 45 {y-10} 505 30 re f')
   text(55,y,13,f'{scenario} | {year} | {1000+100*year:.2f} | {ratio:.2f}')
  text(50,292,11,'Validation rule: end value = principal x ratio / 100.')
  text(50,268,11,'Rows are intentionally malformed in negative samples.')
  text(50,52,9,'Demo template v1 / Page 1')
  stream=DecodedStreamObject();stream.set_data('\n'.join(content).encode('ascii'));page[NameObject('/Contents')]=writer._add_object(stream)
  with (directory/f'{case}.pdf').open('wb') as output:writer.write(output)
if __name__=='__main__':
 generate(Path(__file__).parent/'samples');print('Generated five synthetic PDFs in samples/')
