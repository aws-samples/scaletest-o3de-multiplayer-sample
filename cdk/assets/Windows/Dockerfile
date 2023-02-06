# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# use server core base image
FROM mcr.microsoft.com/windows/servercore:ltsc2019

# get & install Visual C++ redistributable
ADD https://aka.ms/vs/17/release/vc_redist.x64.exe /vc_redist.x64.exe
RUN C:\vc_redist.x64.exe /quiet /install

# copy release game into container file system
COPY project c:/project
