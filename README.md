# R.A.D.A.R. — Rastreamento Automático de Ativos de Rede

Sistema em desenvolvimento para inventariar ativos de TI que respondem a consultas SNMP. O projeto está sendo migrado de um protótipo simulado para uma aplicação Python multiplataforma, acessada pelo navegador na rede local.

> **Estado atual:** o código importado ainda é um protótipo dependente de Docker para simulação e contém dependências de coleta que precisam ser substituídas. Ainda não está pronto para uso em uma rede de produção.

## Objetivo do MVP

- Executar a aplicação principal em Linux e Windows sem exigir Docker.
- Consultar SNMP v1, v2c e v3 em sub-redes explicitamente configuradas pelo administrador.
- Inventariar os tipos de equipamentos cobertos pelo projeto base e mostrar “não informado” quando um equipamento não expuser determinado dado.
- Oferecer painel web com autenticação, perfis, histórico de varreduras, relatórios e gestão de licenças.
- Manter Docker como recurso opcional para simular dispositivos durante o desenvolvimento.

O escopo e os critérios de aceite estão detalhados em [`docs/requisitos-mvp.md`](docs/requisitos-mvp.md). A documentação original do protótipo foi preservada em [`docs/prototipo-base.md`](docs/prototipo-base.md).

## Situação da migração

- [x] Importado o código do projeto base para este repositório local.
- [x] Registrados os requisitos iniciais do MVP.
- [ ] Substituir a coleta SNMP por uma implementação multiplataforma.
- [ ] Configurar descoberta segura em múltiplas sub-redes e perfis de credenciais SNMP.
- [ ] Implementar autenticação e perfis de acesso.
- [ ] Completar histórico, retenção, gestão de licenças e relatórios para uso real.
- [ ] Documentar e validar instalação em Linux e Windows.
- [ ] Validar com a empresa piloto, mediante autorização.

## Execução

As instruções herdadas de Docker e simuladores descrevem apenas o protótipo. Instruções de instalação nativa serão publicadas após a migração do coletor e da configuração da aplicação.

## Segurança

Configure somente redes autorizadas. Credenciais SNMP não são as senhas de administrador do Windows ou Linux. Não armazene segredos em arquivos versionados, issues ou relatórios. SNMP v1/v2c não protegem a community com criptografia; prefira SNMPv3 com autenticação e privacidade quando houver suporte.

## Documentação

- [Requisitos do MVP](docs/requisitos-mvp.md)
- [README do protótipo original](docs/prototipo-base.md)

## Prazo acadêmico

O prazo informado para o projeto é **29/11/2026**. A documentação acadêmica será atualizada conforme os resultados de pesquisa e do piloto, seguindo as normas ABNT aplicáveis.
