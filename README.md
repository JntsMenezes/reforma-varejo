# Reforma no Varejo

Simulador do imposto embutido no preço de três negócios fictícios (farmácia, mercadinho e pet shop) hoje e no regime CBS/IBS de 2033.

**Página:** https://jntsmenezes.github.io/reforma-varejo/

## De onde vêm os números

Quem enquadra cada item é a [calculadora oficial da Receita Federal](https://github.com/ReceitaFederal/calculadora-rtc-regime-regular) (licença MIT), rodando localmente. Ela devolve a redução de alíquota, a base legal da LC 214/2025 e a memória de cálculo. Quando o NCM não bate com a classificação tributária, ela rejeita o item.

O imposto de hoje (ICMS ou ISS, PIS/COFINS e IPI) é uma estimativa por categoria, para SP. Na página dá para editar esses percentuais e as alíquotas de referência de 2033.

## Como gerar a página

1. Clone a calculadora da Receita em `calculadora/`, gere o banco e suba a API em `localhost:8080`, conforme o README dela (precisa de Java 21).
2. Edite os produtos em `dados/produtos.csv`.
3. Rode `python calcular.py`. O script chama a API, confere cada resultado e grava `index.html`.

## Limites

Não entram na conta os créditos de entrada da loja, o Simples Nacional, os anos de transição (2027–2032), o ICMS-ST com MVA, o Imposto Seletivo e o cashback. Lojas, produtos, preços e volumes são fictícios.
