#include <config.h>
#include <Python.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/select.h>
#include <sys/ioctl.h>
#include <stdio.h>   /* Standard input/output definitions */
#include <string.h>  /* String function definitions */
#include <unistd.h>  /* UNIX standard function definitions */
#include <fcntl.h>   /* File control definitions */
#include <errno.h>   /* Error number definitions */
#include <termios.h> /* POSIX terminal control definitions */
#define MAX_STRING_LENGTH = 1024
#define SEND_DELAY  0.10 * 10000L

unsigned long current_time_in_seconds(void){
  struct timeval timenow;
  gettimeofday(&timenow,NULL);
  return 1L * timenow.tv_sec;
}

static PyObject* 
py_open_port(PyObject* self, PyObject* args) {
	
	char *path;
	PyArg_ParseTuple(args, "s", &path);

	int fd = open(path, O_RDWR|O_EXCL|O_NONBLOCK|O_NOCTTY);
	struct termio options;
	if (ioctl(fd,TCGETA,&options) < 0){
		printf("No puedo optener control sobre el %s\n",path);
		return Py_BuildValue("i", -1);
	}
	/* Save actual options */
	int speed=options.c_cflag & CBAUD;
	int bits=options.c_cflag & CSIZE;
	int clocal=options.c_cflag & CLOCAL;
	int stopbits=options.c_cflag & CSTOPB;
	int parity=options.c_cflag & (PARENB | PARODD);
	
	options.c_iflag &= ~(IGNCR | ICRNL | IUCLC | INPCK | IXON | IXANY | IGNPAR );
	options.c_oflag &= ~(OPOST | OLCUC | OCRNL | ONLCR | ONLRET);
	options.c_lflag &= ~(ICANON | XCASE | ECHO | ECHOE | ECHONL);
	options.c_lflag &= ~(ECHO | ECHOE);
	options.c_cc[VMIN] = 1;
	options.c_cc[VTIME] = 0;
	options.c_cc[VEOF] = 1;
	options.c_cflag &= ~(CBAUD | CSIZE | CSTOPB | CLOCAL | PARENB);
    
	options.c_cflag |= (speed | bits | CREAD | clocal | parity | stopbits );
    
	if (ioctl(fd, TCSETA, &options) < 0) {
		printf("Can't change port options");
		return Py_BuildValue("i", -1);;
	}
	usleep(600000);
	
	return Py_BuildValue("i", fd);
} 

static PyObject* 
py_write_string (PyObject* self, PyObject* args){
 	char *string; 
 	int fd ;

 	PyArg_ParseTuple(args, "is", &fd,  &string); 

	int res;
	unsigned int a;
	char ch;
	int written = 0;
	write(fd, string, strlen(string));
	return Py_BuildValue("s", string);
}

int read_one_byte(int fd){    
	fd_set set;
	int res;
	char ch;  
	struct timeval timeout;
	timeout.tv_sec=0L;
	timeout.tv_usec=10000;
	FD_ZERO(&set);
	FD_SET(fd, &set);  
	res=select(fd+1,&set,NULL,NULL,&timeout);  
	if(res) {
		res=read(fd,&ch,1);
		if(res==1) {      
			return(ch);
		}
	} else {
		return(-1);
	}  
	return(0); 
}

static PyObject* 
py_read_string(PyObject* self, PyObject* args) {
	
	int fd;
	long timeout;
	char result[1024];
	
	PyArg_ParseTuple(args, "il", &fd, &timeout);

	char *terminators = "\n\r";
	unsigned long maximun_time = current_time_in_seconds() + timeout;
	int goahead=1;
	char c;
	int terminator_idx = 0;
	int result_idx = 0;
	result[0] = '\0';
  
	while(goahead && (current_time_in_seconds() < maximun_time)){           
		c=read_one_byte(fd);      
		if (c !=-1){        
			/* Compruebo si es un terminador*/
			for(terminator_idx=0;terminator_idx<strlen(terminators);terminator_idx++) {
				if(c==terminators[terminator_idx]) goahead=0;
			}
			if (goahead == 0 && result_idx ==0) {
				//ignoro los terminadores al comienzo d ela cadena
				goahead =1;
			}else if(goahead){
				result[result_idx++] = c;
				result[result_idx] = '\0';
			}          
		}
	}
	if(goahead){
		printf ("TIMEOUT ERROR '%s' \n", result);
		return Py_BuildValue("s", NULL);
	}else{
		return Py_BuildValue("s", result);
	}
}

static PyObject* 
py_flush_buffers(PyObject* self, PyObject* args){
	int fd;

	PyArg_ParseTuple(args, "i", &fd);

	return Py_BuildValue("i", tcflush(fd,TCIOFLUSH));
}

static PyObject* 
py_close_port(PyObject* self, PyObject* args){
	int fd;

	PyArg_ParseTuple(args, "i", &fd);
	usleep(200000);

	return Py_BuildValue("i", close(fd));
}



static PyMethodDef mdpc_methods[] = {
	{"open", py_open_port, METH_VARARGS},
	{"write_string", py_write_string, METH_VARARGS},
	{"read_string", py_read_string, METH_VARARGS},
	{"close",py_close_port, METH_VARARGS}, 
	{"flush", py_flush_buffers, METH_VARARGS}, 
	{NULL, NULL}
};



DL_EXPORT(void)
initmdpc(void) {
	(void) Py_InitModule("mdpc", mdpc_methods);
}
