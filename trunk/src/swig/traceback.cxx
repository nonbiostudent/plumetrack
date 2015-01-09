/* Copyright (C) Nial Peters 2014
 *
 * This file is part of pydoas.
 *
 * pydoas is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * pydoas is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERC HANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with pydoas.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "traceback.h"

//TODO - access to these needs to be made threadsafe.
traceback_entry_t * traceback[MAX_TRACE_ENTRIES];
int traceback_idx = 0;


#define TRACE_HEADER_STR "\n----------------------------------\nTraceback (most recent call last):\n----------------------------------\n"

#define TRACE_EMPTY_STR "No available traceback entries.\n"

#define TRACE_NULL_STR "Traceback entry is NULL!\n"

#define TRACE_ENTRY_STR "%s (line %d): In function '%s':\n    %s\n\n"


///////////////////////////////////////////////////////////////////////////////

void
setTracebackEntry(const char *filename, const int lineno, const char *func_name,
		          const char *message, ...){

	va_list args;

	//create new traceback entry
	traceback[traceback_idx] = new traceback_entry_t;
	if(traceback[traceback_idx] == NULL){
		printf("\ntraceback.c: In function '%s':\n"
		       "traceback.c:%d: Fatal error! Failed to allocate memory "
			   "for error message.\nError message was: '"
			   "%s:%d:%s'\n", __func__,__LINE__,filename, lineno, message);
		
		//this is unrecoverable
		clearErrors();
		exit(1);
	}

	//populate the traceback entry with the supplied values
	strncpy(traceback[traceback_idx]->filename, filename, 100);
	traceback[traceback_idx]->lineno = lineno;
	strncpy(traceback[traceback_idx]->func_name, func_name, 100);

	va_start(args, message);
	vsnprintf(traceback[traceback_idx]->message, 500, message, args);
	va_end(args);

	traceback_idx++;
}

///////////////////////////////////////////////////////////////////////////////

void
clearErrors(void){

	int i;

	for(i=0; i<MAX_TRACE_ENTRIES; i++){

		if (traceback[i] != NULL){
			delete traceback[i];
			traceback[i] = NULL;
		}
	}
	
	traceback_idx = 0;
}

///////////////////////////////////////////////////////////////////////////////

static int
getTracebackStrMaxLen(void){

	if (traceback_idx > 0){

		return strlen(TRACE_HEADER_STR) + strlen(TRACE_NULL_STR) +
			   traceback_idx * (4 + strlen(TRACE_ENTRY_STR) + sizeof(traceback_entry_t)) + 1; //+4 to account for size of lineno, +1 for null byte
	}

	return strlen(TRACE_HEADER_STR) + strlen(TRACE_EMPTY_STR) + 1;
}

///////////////////////////////////////////////////////////////////////////////

char *
getTracebackStr(void){

	int i;
	traceback_entry_t *tb;
	char *traceback_str = (char *) malloc(getTracebackStrMaxLen());

	if (traceback_str == NULL){
		return NULL;
	}

	sprintf(traceback_str,"%s",TRACE_HEADER_STR);

	if (traceback_idx == 0){
		sprintf(traceback_str + strlen(traceback_str), "%s",TRACE_EMPTY_STR);
		return traceback_str;
	}

	for (i = traceback_idx - 1; i>=0; i--){
	        tb = traceback[i];

	        if (tb == NULL){
	            sprintf(traceback_str+strlen(traceback_str), "%s",TRACE_NULL_STR);
	            continue;
	        }

	        sprintf(traceback_str+strlen(traceback_str), TRACE_ENTRY_STR, traceback[i]->filename,
	               traceback[i]->lineno, traceback[i]->func_name,
	               traceback[i]->message);

	    }

	return traceback_str;

}

//////////////////////////////////////////////////////////////////////////////

void
printTraceback(void){
    
    char *tb_str = getTracebackStr();
    printf("%s", tb_str);
    free(tb_str);
    
}

///////////////////////////////////////////////////////////////////////////////

void
setPythonTraceback(void){
	char *tb_str = getTracebackStr();
	const char *start = "A problem occurred in an extension module. See the following traceback:\n";
	char *whole_str = (char *) malloc(strlen(tb_str)+ strlen(start) + 2);
	sprintf(whole_str, "%s%s", start, tb_str);

	PyErr_SetString(PyExc_RuntimeError, whole_str);

	free(tb_str);
	free(whole_str);
	clearErrors();
}
