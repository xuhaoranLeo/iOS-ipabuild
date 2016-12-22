#!/usr/bin/env python
# -*- coding:utf-8 -*-

#
# ipa自动打包上传脚本
# 使用说明：
#		编译project
#			./ipabuild.py -p -u -g e578f0d
#			./ipabuild.py -p otherproject.project -t othertarget -u -g e578f0d
#		编译workspace
#			./ipabuild.py -w -u -g e578f0d
#			./ipabuild.py -w otherworkspace.workspace -s otherscheme -u -g e578f0d
#
# 参数说明:  -w workspace			使用workspace进行打包，默认为全局变量PROJECT_NAME
#			-s scheme			与workspace对应使用，默认为全局变量PROJECT_NAME
#			-p project			使用project进行打包，默认为全局变量PROJECT_NAME
#			-t target			与project对应使用，默认为全局变量PROJECT_NAME	
#			-u upload			上传到Web开关，对应配置为UPLOAD_URL与UPLOAD_DATA
#			-g gitversion		git该版本短号，如e578f0d，用于标记ipa
#
# 备注：
#		ipa命名规则：PROJECT_NAME+GIT_VERSION+CURRENT_TIME
#		ipa与dSYM导出地址：OUTPUT_PATH/PROJECT_NAME+GIT_VERSION+CURRENT_TIME/
#


from optparse import OptionParser
import subprocess
import requests
import time
import os

####################################################################################################
#configuration for iOS build setting

PROJECT_NAME = "FHSupportOldAge"
OUTPUT_PATH = "~/Desktop"
SDK = "iphoneos"
# ---开发包---
# CODE_SIGN_IDENTITY= ""
# PROVISIONING_PROFILE= ""
# CONFIGURATION = "Debug"

# ---adhoc包---
CODE_SIGN_IDENTITY= ""
PROVISIONING_PROFILE= ""
CONFIGURATION = "Release"

# ---企业包---
# CODE_SIGN_IDENTITY= ""
# PROVISIONING_PROFILE= ""
# CONFIGURATION = "Release"

UPLOAD_URL = ""
UPLOAD_DATA = {'OS':"iOS", 'APPID':"1", 'VERSION':"1.0.2"}
####################################################################################################


def cleanBuildDir(buildDir):
	cleanCmd = "rm -r %s" %(buildDir)
	process = subprocess.Popen(cleanCmd, shell = True)
	process.wait()
	print "cleaned buildDir: %s" %(buildDir)


def backupsDSYM(signApp, output):
	backupsCmd = "cp -R %s.dSYM %s.dSYM" % (signApp, output)
	process = subprocess.Popen(backupsCmd, shell = True)
	process.wait()


def parserUploadResult(jsonResult):
	resultCode = jsonResult['code']
	if resultCode == 1:
		print "**********Upload Success***********"
		print "Download URL:" + jsonResult['data']
	else:
		print "**********Upload Fail**********"
		print "Fail Reason:"+jsonResult['message']


def uploadIPA(path):
	ipaPath = os.environ['HOME'] + '/Desktop' + path
	print "ipaPath:" + ipaPath
	files = {'file': open(ipaPath, 'rb')}
	headers = {'enctype': 'multipart/form-data'}
	uploadData = UPLOAD_DATA
	print "uploading...."
	r = requests.post(UPLOAD_URL, data = uploadData ,files=files,headers=headers)
	if r.status_code == requests.codes.ok:
		result = r.json()
		parserUploadResult(result)
	else:
		print 'HTTPError,Code:'+r.status_code


def buildProject(project, target, output):
	#手动证书
	buildCmd = 'xcodebuild -project %s -target %s -sdk %s -configuration %s build CODE_SIGN_IDENTITY="%s" PROVISIONING_PROFILE="%s"' %(project, target, SDK, CONFIGURATION, CODE_SIGN_IDENTITY, PROVISIONING_PROFILE)
	#自动证书
	# buildCmd = 'xcodebuild -project %s -target %s -sdk %s -configuration %s build"' %(project, target, SDK, CONFIGURATION)
	process = subprocess.Popen(buildCmd, shell = True)
	process.wait()

	signApp = "./build/%s-iphoneos/%s.app" %(CONFIGURATION, target)
	signCmd = "xcrun -sdk %s -v PackageApplication %s -o %s" %(SDK, signApp, output)
	process = subprocess.Popen(signCmd, shell=True)
	(stdoutdata, stderrdata) = process.communicate()
	backupsDSYM(signApp, output)
	cleanBuildDir("./build")


def buildWorkspace(workspace, scheme, output):
	process = subprocess.Popen("pwd", stdout=subprocess.PIPE)
	(stdoutdata, stderrdata) = process.communicate()
	buildDir = stdoutdata.strip() + '/build'
	#手动证书
	buildCmd = 'xcodebuild -workspace %s -scheme %s -sdk %s -configuration %s build CODE_SIGN_IDENTITY="%s" PROVISIONING_PROFILE="%s" SYMROOT=%s' %(workspace, scheme, SDK, CONFIGURATION, CODE_SIGN_IDENTITY, PROVISIONING_PROFILE, buildDir)
	#自动证书
	# buildCmd = 'xcodebuild -workspace %s -scheme %s -sdk %s -configuration %s build SYMROOT=%s' %(workspace, scheme, SDK, CONFIGURATION, buildDir)
	process = subprocess.Popen(buildCmd, shell = True)
	process.wait()

	signApp = "./build/%s-%s/%s.app" %(CONFIGURATION, SDK, scheme)
	signCmd = "xcrun -sdk %s -v PackageApplication %s -o %s" %(SDK, signApp, output)
	process = subprocess.Popen(signCmd, shell=True)
	(stdoutdata, stderrdata) = process.communicate()
	backupsDSYM(signApp, output)
	cleanBuildDir(buildDir)


def configePackageConfig(options):
	project = options.project
	workspace = options.workspace
	target = options.target
	scheme = options.scheme
	upload = options.upload
	gitversion = options.gitversion
	t = time.strftime('%m-%d-%H-%M',time.localtime(time.time()))
	ipaName = "%s_%s_%s" %(scheme, gitversion, t)
	fileName = "%s/%s" %(OUTPUT_PATH, ipaName)
	mkdirCmd = "mkdir %s" %(fileName)
	process = subprocess.Popen(mkdirCmd, shell = True)
	process.wait()

	#清理项目
	cleanCmd = 'xcodebuild clean'
	process = subprocess.Popen(cleanCmd, shell = True)
	process.wait()

	#打包
	output = "%s/%s.ipa" %(fileName, ipaName)
	if workspace is not None:
		buildWorkspace(workspace, scheme, output)
	elif project is not None:
		buildProject(project, target, output)
	#上传
	if upload is 'True':
		uploadIPA("/%s/%s.ipa" %(ipaName, ipaName))


def optional_arg(arg_default):
	def func(option,opt_str,value,parser):
		if parser.rargs and not parser.rargs[0].startswith('-'):
			val=parser.rargs[0]
			parser.rargs.pop(0)
		else:
			val=arg_default
		setattr(parser.values,option.dest,val)
	return func
	

def main():
	parser = OptionParser();
	parser.add_option('-w', '--workspace', help="name.xcworkspace", action='callback', callback=optional_arg(PROJECT_NAME+'.xcworkspace'), dest='workspace')
	parser.add_option('-p', '--project', help="name.xcodeproj.", action='callback', callback=optional_arg(PROJECT_NAME+'.xcodeproj'), dest='project')
	parser.add_option("-s", "--scheme", help="scheme name", action="store", default=PROJECT_NAME)
	parser.add_option("-t", "--target", help="target name", action="store", default=PROJECT_NAME)
	parser.add_option('-u', '--upload', help="upload ipa", action='callback', callback=optional_arg('True'), dest='upload', default="False")
	parser.add_option("-g", "--gitversion", help="git short version code", default="aaaaaa")
	(options, args) = parser.parse_args()
	print "options: %s, args: %s" % (options, args)
	configePackageConfig(options)


if __name__ == '__main__':
	main()