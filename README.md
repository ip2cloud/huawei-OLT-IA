# Huawei ONT Management Tool

This project provides a tool for managing ONTs (Optical Network Terminals) on Huawei OLTs (Optical Line Terminals), allowing operations such as status checking, resetting, and listing ONTs.

## Installation and Configuration

### 1. Configure Environment Variables

Copy the `.env.example` file to `.env` and adjust the variables as needed:

```bash
cp .env.example .env
```

Edit the `.env` file with the desired configurations:

```env
# Image Configurations
REGISTRY_URL=docker.io/asabocinski
IMAGE_NAME=ont-manager
VERSION=1.0.0

# Container Configurations
PLATFORM=linux/arm64
TZ=America/Sao_Paulo
SSH_PORT=2222
```

### 2. Start the Container

Run the following command to start the container:

```bash
docker-compose -f docker-compose-selfhost.yaml up -d
```

### 3. Verify if it's Running

Check if the container is running with the command:

```bash
docker-compose -f docker-compose-selfhost.yaml ps
```

## Usage

The `huawei-ont-manager.sh` script offers several operations to manage ONTs:

### 1. Check Status of a Single ONT

```bash
./huawei-ont-manager.sh status -o HOST FRAME SLOT PORT ONT USERNAME PASSWORD [-v|--verbose]

# Example:
./huawei-ont-manager.sh status -o 172.16.0.13 0 5 2 0 admin senha123 --verbose
```

### 2. Reset a Single ONT

```bash
./huawei-ont-manager.sh reset -o HOST FRAME SLOT PORT ONT USERNAME PASSWORD [-v|--verbose]

# Example:
./huawei-ont-manager.sh reset -o 172.16.0.13 0 5 2 0 admin senha123 --verbose
```

### 3. Batch Operations

```bash
./huawei-ont-manager.sh reset -l HOST FRAME SLOT ONTS USERNAME PASSWORD [-v|--verbose]

# Example:
./huawei-ont-manager.sh reset -l 172.16.0.13 0 5 '[{"port":2,"ont":0},{"port":2,"ont":1}]' admin senha123 --verbose
```

### 4. List ONTs of a Port

```bash
./huawei-ont-manager.sh ont-summary HOST FRAME SLOT PORT USERNAME PASSWORD [-v|--verbose]

# Example:
./huawei-ont-manager.sh ont-summary 172.16.0.13 0 5 2 admin senha123 --verbose
```

## Creating a New Version

To create a new version of the project, follow these steps:

1. Make the necessary changes to the source code.

2. Update the version number in the `.env` file:

```env
VERSION=new_version
```

3. Build the new image using the `install.sh` script:

```bash
./install.sh -t new_version
```

This command will build the new image with the specified tag.

Now, when running:

```bash
./install.sh -v -t 0.1.3
```

The script will detect that it's a multi-platform build without --push and display a clear error message with the available options:

1. Use --push to push to a registry
2. Specify a single platform (-p arm64 or -p amd64)

For local builds, you must specify the platform:

```bash
./install.sh -v -t 0.1.3 -p arm64
```

For multi-platform builds, you must use --push with registry or repository:

```bash
./install.sh -v -t 0.1.3 --push -r youruser
```

4. Start the container with the new version:

```bash
docker-compose -f docker-compose-selfhost.yaml up -d
```

This will replace the running container with the new version.

5. Verify that the new version is running correctly:

```bash
docker-compose -f docker-compose-selfhost.yaml ps
```

6. Optionally, push the new image to a Docker registry:

```bash
./install.sh -t new_version --push -r your_user
```

This will push the image to the specified registry.

## Parameters

- `HOST`: IP or hostname of the OLT
- `FRAME`: Frame number (usually 0)
- `SLOT`: Slot number
- `PORT`: Port number
- `ONT`: ONT ID
- `USERNAME`: OLT access username
- `PASSWORD`: OLT access password
- `-v|--verbose`: Enables verbose mode with more information

Refer to the documentation of the `huawei-ont-manager.sh` script for more details on parameters and usage examples.

## Troubleshooting

Refer to the "Troubleshooting" section of the original README for tips on solving common issues.
