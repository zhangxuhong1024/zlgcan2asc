pyinstaller -w -F -i logo.ico zlgcan2asc.pyw
cp -av ./dist/zlgcan2asc.exe .
rm -rf ./build
rm -rf ./__pycache__
rm -rf ./dist
rm -rf ./zlgcan2asc.spec
@pause 
