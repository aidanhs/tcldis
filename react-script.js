npm install react-tools uglify-js
export PATH=$(pwd)/node_modules/.bin:$PATH
cat tcldis/web/script.js | jsx | uglifyjs - --compress --mangle --screw-ie8 > script.min.js