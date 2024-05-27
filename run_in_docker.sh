cd web
docker build ./ -t ai-study-web 
cd ..
cd api 
docker build ./ -t ai-study-api

cd ..

docker compose up -d

