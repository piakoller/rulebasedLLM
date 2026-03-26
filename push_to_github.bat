@echo off
git init
git add .
git commit -m "Initial commit with Frame Manager and Clinical GraphRAG"
git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/piakoller/rulebasedLLM.git
git push -u origin main
