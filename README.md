# las2heightmap

## Build

```
docker build -t las2heightmap .
```

## Run

```
docker run --rm -v .:/data las2heightmap -i /path/to/input.las -o /path/to/output.png -W 2048 -H 2048
```or
docker run --rm -v $(pwd):/data las2heightmap -i /data/input.las -o ~/data/output.png -W 2048 -H 2048

