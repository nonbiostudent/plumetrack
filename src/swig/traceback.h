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
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with pydoas.  If not, see <http://www.gnu.org/licenses/>.
 */
#ifndef __TRACEBACK_H
#define __TRACEBACK_H
#include<Python.h>
#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<stdarg.h>

#define MAX_TRACE_ENTRIES 30

#define ERROR(message,...) setTracebackEntry(__FILE__, __LINE__, __func__, message, ##__VA_ARGS__)


typedef struct traceback_entry_t {
	char filename[100];
	int lineno;
	char func_name[100];
	char message[500];
} traceback_entry_t;


//char * getTraceback(void);
void setTracebackEntry(const char *filename, const int lineno, const char *func_name, const char *message, ...);
void clearErrors(void);
void printTraceback(void);
void setPythonTraceback(void);

extern traceback_entry_t * traceback[MAX_TRACE_ENTRIES];
extern int traceback_idx;

#endif
